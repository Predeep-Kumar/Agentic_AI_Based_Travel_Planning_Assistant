from datetime import datetime, timedelta, date
import random
import re
from agent.intent_parser import parse_travel_intent
from agent.llm_loader import load_llm

from tools.flight_tool import search_flights
from tools.hotel_tool import search_hotels
from tools.places_tool import search_places
from tools.weather_lookup_tool import weather_lookup
from tools.budget_tool import estimate_trip_budget
from utils.flight_city_extractor import FlightCityExtractor


class TravelAgent:
    def __init__(self, force_local=False, local_model_choice=None):
        model_info = load_llm(
            force_local=force_local,
            local_model_choice=local_model_choice
        )
        self.force_finalize = False
        self.city_extractor = FlightCityExtractor(
            json_path="data/flights.json"
        )

        self.llm = model_info["instance"]
        self.model_provider = model_info["provider"]
        self.model_name = model_info["model_name"]
        self.model_status = model_info["status"]
        self.model_info = model_info

        self.state = {
            "started": False,
            "source": None,
            "destination": None,
            "trip_type": None,  
            "travel_date": None,
            "return_date": None,
            "days": None,
            "travelers": None,
            "preferences": {
                "budget": None,
                "interests": []
            },
            "return_resolved": False
        }

        self.pending_slot = None
        self.pending_outbound_options = None
        self.pending_return_options = None
        self._reflection_count = 0
        self._parsed_this_turn = False
        
    
    def _reset_state(self):
       
        self.state = {
            "started": False,
            "source": None,
            "destination": None,
            "trip_type": None,
            "travel_date": None,
            "return_date": None,
            "days": None,
            "travelers": None,
            "preferences": {
                "budget": None,
                "interests": []
            },
            "return_resolved": False
        }
        self.pending_slot = None
        self.pending_outbound_options = None
        self.pending_return_options = None
        self._reflection_count = 0
        self._parsed_this_turn = False
        
        
    def _validate_current_state(self):
        #  Source validation
        if (
            self.state["source"]
            and self.pending_slot is None
            and not self.city_extractor.is_valid_source(
                self.city_extractor.normalize(self.state["source"])
            )
        ):
            
            self.pending_slot = "source" 
            return {
                "status": "NEED_INPUT",
                "question": (
                    f"❌ Flights are not available from **{self.state['source']}**.\n\n"
                    f"Available departure cities:<br>"
                    + "<br>".join(
                        f"• {c}" for c in self.city_extractor.all_sources()
                    )
                    + "\n\nPlease enter a valid departure city or type **cancel**."
                )
            }

        #  Destination / Route validation
        if self.state["source"] and self.state["destination"]:
            if self.state["destination"]:
                cleaned = self._extract_city(self.state["destination"])
                if cleaned:
                    self.state["destination"] = cleaned

            src = self.city_extractor.normalize(self.state["source"])
            dst = self.city_extractor.normalize(self.state["destination"])

            if self.pending_slot != "destination" and not self.city_extractor.is_valid_destination(dst):
                self.pending_slot = "destination"  
                return {
                "status": "NEED_INPUT",
                "question": (
                    f"❌ **{self.state['destination']}** is not a supported destination.\n\n"
                    f"Available destinations from **{src}**:<br>"
                    + "<br>".join(
                        f"• {d}" for d in self.city_extractor.destinations_from(src)
                    )
                    + "\n\nPlease choose a destination or type **cancel**."
                )
            }

            if self.pending_slot != "destination" and not self.city_extractor.is_valid_route(src, dst):
                self.pending_slot = "destination"   
                return {
                    "status": "NEED_INPUT",
                    "question": (
                        f"🚫 No flights available from **{src} → {dst}**.\n\n"
                        f"You can travel from {src} to:\n"
                        + "\n".join(self.city_extractor.destinations_from(src))
                        + "\n\nPlease select a destination or type **cancel**."
                    )
                }

        #  Travel date validation
        if self.state["travel_date"]:
            d = datetime.fromisoformat(self.state["travel_date"]).date()
            if d < date.today():
                self.pending_slot = "travel_date"  
                return {
                    "status": "NEED_INPUT",
                    "question": (
                        "⚠️ Travel date must be in the future.\n\n"
                        "Please enter a valid date (YYYY-MM-DD) or type **cancel**."
                    )
                }
        
        return None


    # Missing slot

    def _missing_slot(self):
        order = [
            ("source", "Where will you travel from?"),
            ("destination", "Where would you like to travel to?"),
            ("trip_type", "Is this a one-way trip or a round trip? (one-way / round-trip)"),
            ("travel_date", "What is your travel date? (YYYY-MM-DD)"),
            ("days", "How many days is your trip?"),
            ("travelers", "How many people are traveling?")
        ]

        for k, q in order:
            if self.state[k] is None:
                return k, q

        if not self.state["preferences"]["budget"]:
            return "budget", "What is your budget preference? (budget / mid-range / luxury)"

        return None, None

    # SMART REFLECTION LAYER
 
    def _build_reflective_prompt(self, next_question: str) -> str:
        import random
        from datetime import datetime

        self._reflection_count += 1


        # Friendly openers (high variety)
        openers = [
            "That sounds exciting!",
            "Nice choice!",
            "Love where this is going!",
            "Great plan so far!",
            "This trip is shaping up nicely!",
            "Awesome, let’s keep going!",
            "Perfect, I’m following you.",
            "Sounds like a fun trip already!"
        ]

        confirmations = [
            "Got it 👍",
            "Alright!",
            "Perfect.",
            "Sounds good.",
            "Understood.",
            "All set so far."
        ]

        # Build factual summary dynamically

        facts = []

        if self.state.get("source") and self.state.get("destination"):
            facts.append(
                f"traveling from **{self.state['source']}** to **{self.state['destination']}**"
            )
        elif self.state.get("destination"):
            facts.append(f"heading to **{self.state['destination']}**")

        if isinstance(self.state.get("travelers"), int):
            t = self.state["travelers"]
            facts.append(f"{t} traveler{'s' if t > 1 else ''}")

        if self.state.get("trip_type"):
            facts.append(
                "a round trip" if self.state["trip_type"] == "round_trip" else "a one-way trip"
            )

        if self.state.get("travel_date"):
            try:
                d = datetime.fromisoformat(self.state["travel_date"]).strftime("%b %d, %Y")
                facts.append(f"starting on **{d}**")
            except Exception:
                pass

        if self.state.get("days"):
            facts.append(f"for **{self.state['days']} days**")

        if self.state["preferences"].get("budget"):
            facts.append(f"with a **{self.state['preferences']['budget']}** budget")

        # Human-style summary sentence
        summary_templates = [
            "So far, I’ve got that you’re {}.",
            "Here’s what I understand until now: {}.",
            "Just to confirm, you’re {}.",
            "Up to this point, it looks like you’re {}.",
            "Let me recap quickly — you’re {}."
        ]

        summary = ""
        if facts:
            summary = random.choice(summary_templates).format(", ".join(facts))

        # First few turns → richer tone
        if self._reflection_count <= 3:
            parts = [
                random.choice(openers),
                summary,
                next_question
            ]
            return "\n\n".join(p for p in parts if p).strip()

        # Later turns → concise & natural
        return f"{random.choice(confirmations)} {next_question}"


    # helpers
    
    
    def _is_trigger_only(self, text: str) -> bool:
        text = text.lower().strip()
        return text in {
            "plan a trip",
            "plan trip",
            "start trip",
            "travel",
            "trip",
            "vacation",
            "holiday"
        }

    def _parse_human_date(self, text: str):
        """
        Converts human-friendly dates to ISO format.
        Examples:
        - 29 dec
        - 29 december
        - dec 29
        - 29 dec 2025
        """
        text = text.lower().strip()

        formats = [
            "%d %b %Y", "%d %B %Y",
            "%b %d %Y", "%B %d %Y",
            "%d %b", "%d %B",
            "%b %d", "%B %d"
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(text, fmt)

                # If year not provided → assume next occurrence
                if "%Y" not in fmt:
                    parsed = parsed.replace(year=date.today().year)
                    if parsed.date() < date.today():
                        parsed = parsed.replace(year=parsed.year + 1)

                return parsed.date().isoformat()
            except ValueError:
                continue

        return None

    def _build_fallback_response(self):
        """
        Smart fallback handler:
        1) If conversation not started → guide user to start with 'plan a trip'
        2) If conversation started → give slot-specific correction
        """

        # CASE 1: Conversation NOT started

        if not self.state.get("started"):
            return {
                "status": "NEED_INPUT",
                "question": (
                    "Hey there 🙂 I’m here to help you plan a trip.\n\n"
                    "To get started, just type something like:\n"
                    "👉 **plan a trip**"
                )
            }

        # CASE 2: Conversation started, wrong input

        slot = self.pending_slot

        # Slot-specific guidance (clean & focused)
        slot_guidance = {
            "source": "Please enter the **departure city** (for example: Delhi, Mumbai).",
            "destination": "Please enter the **destination city** (for example: Goa, Manali).",
            "travel_date": "Please enter a **travel date** in YYYY-MM-DD format (for example: 2025-12-30).",
            "days": "Please enter the **number of days** for your trip (for example: 5 days).",
            "travelers": "Please tell me **how many travelers** (for example: 2 travelers).",
            "trip_type": "Please specify the **trip type** (one way or round trip)."
        }

        friendly_openers = [
            "Hmm, I didn’t quite get that 🤔",
            "I might have missed what you meant.",
            "That doesn’t look like what I was asking for."
        ]

        if slot in slot_guidance:
            message = (
                f"{random.choice(friendly_openers)}\n\n"
                f"{slot_guidance[slot]}"
            )
        else:
            # Fallback if slot is unknown (rare)
            message = (
                f"{random.choice(friendly_openers)}\n\n"
                "Please try answering the last question in a simple way."
            )

        return {
            "status": "NEED_INPUT",
            "question": message
        }

        
    def _extract_city(self, text: str):
        """
        Extracts a probable city name from noisy user input.
        Example:
        'Paris Starting From Date' -> 'Paris'
        'change destination to Goa please' -> 'Goa'
        """
        if not text:
            return None

        # Remove dates, numbers, filler words
        noise_words = [
            "starting", "from", "date", "travel", "trip",
            "going", "to", "please", "change", "destination",
            "source", "city", "on"
        ]

        cleaned = text.lower()

        for w in noise_words:
            cleaned = cleaned.replace(w, " ")

        # Keep only letters & spaces
        cleaned = re.sub(r"[^a-z\s]", " ", cleaned)

        # Split words
        tokens = [t for t in cleaned.split() if len(t) > 2]

        if not tokens:
            return None

        if len(tokens) >= 2:
            candidate = f"{tokens[0]} {tokens[1]}".title()
            if self.city_extractor.is_valid_city(candidate):
                return candidate
        return tokens[0].title()
        
    
    
    def _price_diff_text(self, base_price, alt_price):
        if base_price is None or alt_price is None:
            return "price may vary"
        diff = alt_price - base_price
        if diff == 0:
            return "estimated same price"
        return f"+₹{diff}" if diff > 0 else f"-₹{abs(diff)}"

    def _outbound_date_candidates(self, travel_date: date):
        offsets = [-2, -1, 1, 2, 3, 4, 5, 6, 7]
        return sorted({
            travel_date + timedelta(days=o)
            for o in offsets
            if travel_date + timedelta(days=o) > date.today()
        })

    def _return_date_candidates(self, base: date, days: int, start: date):
        options = []

        if 4 <= days <= 14:
            options.append(base - timedelta(days=1))
            options.extend(base + timedelta(days=i) for i in (1, 2, 3))
        else:
            options.extend(base - timedelta(days=i) for i in (1, 2, 3))
            options.extend(base + timedelta(days=i) for i in (1, 2, 3))

        return sorted(d for d in options if d > date.today() and d >= start)


    # DAY WISE ITINERARY
    def _generate_day_wise_itinerary(self, start_date, days, hotel, places, weather=None, outbound_flight=None, return_flight=None):
        itinerary = []
        place_idx = 0

        source = self.state.get("source", "your city")
        destination = self.state.get("destination", "your destination")
        hotel_name = hotel.get("name", "your hotel")

        # WEATHER MAP (SAFE)

        weather_map = {}
        if weather and weather.get("daily_forecast"):
            for w in weather["daily_forecast"]:
                weather_map[w["date"]] = w

        # FLIGHT TIME HELPERS

        def flight_time(f, key):
            try:
                return f.get(key, "").split(",")[-1].strip()
            except Exception:
                return None

        for day in range(1, days + 1):
            current_date = start_date + timedelta(days=day - 1)
            iso_date = current_date.isoformat()
            date_str = current_date.strftime("%d %b %Y")
            weekday = current_date.strftime("%A")

            # Weather sentence (short & natural)
            w = weather_map.get(iso_date)
            weather_text = (
                f"The weather is expected to be {w.get('condition').lower()} with temperatures between "
                f"{w.get('temp_min')}°C and {w.get('temp_max')}°C."
                if w else "Weather conditions are expected to be pleasant."
            )


            # DAY 1 – DEPARTURE + ARRIVAL

            if day == 1:
                dep_time = flight_time(outbound_flight, "departure_time")
                arr_time = flight_time(outbound_flight, "arrival_time")

                travel_line = (
                    f"Depart from {source} and arrive in {destination} on {weekday}, {date_str}."
                )

                if dep_time and arr_time:
                    travel_line = (
                        f"Depart from {source} and arrive in {destination} on "
                        f"{weekday}, {date_str}. Your flight departs around {dep_time} "
                        f"and arrives by {arr_time}."
                    )

                itinerary.append({
                    "day": f"Day {day} ({weekday})",
                    "date": date_str,
                    "plan": (
                        f"{travel_line} After landing, proceed to {hotel_name} using a taxi or cab. "
                        f"Once checked in, take time to rest and recover from the journey.\n\n"
                        f"Later, you may step out to explore nearby streets, cafés, or local attractions "
                        f"at a relaxed pace. {weather_text} Return to the hotel for a comfortable overnight stay."
                    )
                })

            # LAST DAY – RETURN / DEPARTURE
            elif day == days and self.state["trip_type"] == "round_trip":
                ret_time = flight_time(return_flight, "departure_time") if return_flight else None

                departure_line = (
                    f"After checkout from {hotel_name}, prepare for your departure from {destination}."
                )

                if ret_time:
                    departure_line = (
                        f"After checkout from {hotel_name}, prepare for your return journey. "
                        f"Your flight departs around {ret_time}."
                    )

                itinerary.append({
                    "day": f"Day {day} ({weekday})",
                    "date": date_str,
                    "plan": (
                        f"{departure_line} Depending on your schedule, you may enjoy a final stroll, "
                        f"shop for souvenirs, or relax before heading to the airport.\n\n"
                        f"Depart from {destination}, marking the conclusion of a memorable trip. "
                        f"{weather_text}"
                    )
                })
            
            elif day == days and self.state["trip_type"] == "one_way":
                itinerary.append({
                    "day": f"Day {day} ({weekday})",
                    "date": date_str,
                    "plan": (
                        f"This marks the final planned day of your stay in {destination}. "
                        f"After checking out from {hotel_name}, you may explore nearby areas, "
                        f"relax at a café, or prepare for your onward journey.\n\n"
                        f"The trip concludes here based on your selected duration. "
                        f"{weather_text}"
                    )
                })


            # MIDDLE DAYS – SIGHTSEEING
           
            else:
                day_places = places[place_idx:place_idx + 3]
                place_idx += 3

                visit_text = (
                    ", ".join(p.get("name", "a local attraction") for p in day_places)
                    if day_places else "nearby local attractions"
                )

                itinerary.append({
                    "day": f"Day {day} ({weekday})",
                    "date": date_str,
                    "plan": (
                        f"Start the day with breakfast at the hotel and head out to explore {visit_text}. "
                        f"Spend time experiencing the local culture, landmarks, and food spots along the way.\n\n"
                        f"In the later part of the day, return to the hotel to rest or enjoy a casual walk "
                        f"around nearby areas. {weather_text} End the day with dinner and overnight stay."
                    )
                })

        return itinerary



    
    # PAST DATE DETECTOR 
    def _detect_past_date(self, text: str):
        import re
        from datetime import date

        m = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
        if not m:
            return None

        try:
            d = date.fromisoformat(m.group(1))
            if d < date.today():
                return m.group(1)
        except Exception:
            pass

        return None
     
    # MAIN RUN
    def run(self, user_query: str) -> dict:
        import copy
        state_snapshot = copy.deepcopy(self.state)
        self._parsed_this_turn = False
        user_lower = user_query.lower().strip()

        if not user_query or not user_query.strip():
            return {"status": "NEED_INPUT", "question": "Please enter a valid response."}
        
        # ---------- START TRIP TRIGGER ----------
        if not self.state["started"]:
            trigger_words = ["plan", "trip", "travel", "vacation", "holiday", "tour"]

            if not any(w in user_lower for w in trigger_words):
                return {
                    "status": "NEED_INPUT",
                    "question": "👋 Hi! Would you like me to plan a trip for you?"
                }

            
            extracted = parse_travel_intent(self.llm, user_query, self.state.copy())

            for k, v in extracted.items():
                if k == "preferences":
                    self.state["preferences"].update(v)
                else:
                    self.state[k] = v

            self.state["started"] = True

            slot, question = self._missing_slot()
            if slot:
                self.pending_slot = slot
                return {
                    "status": "NEED_INPUT",
                    "question": question
                }
        
        
        # ---------- PAST DATE GUARD (USER FEEDBACK) ----------
        if self.pending_slot != "travel_date":
            past_date = self._detect_past_date(user_query)
            if past_date:
                return {
                    "status": "NEED_INPUT",
                    "question": (
                        f"⚠️ {past_date} is already in the past.\n\n"
                        "Please enter a **future travel date** (YYYY-MM-DD)."
                    )
                }        
                
                
        if user_lower == "cancel":
            self._reset_state()
            return {
                "status": "NEED_INPUT",
                "question": "Trip cancelled. Say **plan a trip** to start again."
            }

    
        # ---------- PENDING OUTBOUND ----------
        if self.pending_outbound_options:
            if user_lower.isdigit():
                idx = int(user_lower) - 1
                if 0 <= idx < len(self.pending_outbound_options):
                    self.state["travel_date"] = self.pending_outbound_options[idx].isoformat()
                    self.pending_outbound_options = None
                else:
                    return {"status": "NEED_INPUT", "question": "Invalid selection."}
            else:
                return {"status": "NEED_INPUT", "question": "Choose a number or type 'cancel'."}

        # ---------- PENDING RETURN ----------
        if self.pending_return_options:
            if user_lower == "one-way":
                self.state["trip_type"] = "one_way"
                self.state["return_date"] = None
                self.state["return_resolved"] = True
                self.pending_return_options = None

            if self.pending_return_options:
                if user_lower == "one-way":
                    self.state["trip_type"] = "one_way"
                    self.state["return_date"] = None
                    self.state["return_resolved"] = True
                    self.pending_return_options = None

                elif user_lower.isdigit():
                    idx = int(user_lower) - 1
                    if 0 <= idx < len(self.pending_return_options):
                        days, new_return = self.pending_return_options[idx]
                        self.state["days"] = days
                        self.state["return_date"] = new_return.isoformat()
                        self.state["return_resolved"] = True
                        self.pending_return_options = None
                    else:
                        return {
                            "status": "NEED_INPUT",
                            "question": "Invalid selection. Please choose a valid number."
                        }
                else:
                    return {"status": "NEED_INPUT", "question": "Choose a number, 'one-way', or 'cancel'."}
            
        

        # ---------- SLOT FILLING ----------
        if self.pending_slot:
            slot = self.pending_slot
            self.pending_slot = None
            try:
                if slot in ("days", "travelers"):
                    value = int(user_query)
                    if value <= 0:
                        return {
                            "status": "NEED_INPUT",
                            "question": f"Please enter a valid positive number for {slot}."
                        }
                    self.state[slot] = value
                    self._reflection_count = 0 

                elif slot == "trip_type":
                    if "round" in user_lower:
                        self.state["trip_type"] = "round_trip"
                        self._reflection_count = 0 
                    elif "one" in user_lower:
                        self.state["trip_type"] = "one_way"
                        self._reflection_count = 0 
                    else:
                        return {
                            "status": "NEED_INPUT",
                            "question": "Please type one-way or round-trip."
                        }

                elif slot == "budget":
                    self.state["preferences"]["budget"] = user_lower
                    self._reflection_count = 0 

                elif slot == "travel_date":
                    iso_date = self._parse_human_date(user_query)

                    if not iso_date:
                        return {
                            "status": "NEED_INPUT",
                            "question": (
                                "I couldn’t understand that date 🤔\n\n"
                                "Please enter something like:\n"
                                "• 2025-12-29\n"
                                "• 29 Dec\n"
                                "• December 29"
                            )
                        }

                    d = datetime.fromisoformat(iso_date).date()
                    if d < date.today():
                        return {
                            "status": "NEED_INPUT",
                            "question": "Please enter a **future date**."
                        }

                    self.state["travel_date"] = iso_date
                    self._reflection_count = 0
                    self.pending_slot = None 

                else:
                    if slot in ("source", "destination"):
                        city = self._extract_city(user_query)
                        if not city:
                            return {
                                "status": "NEED_INPUT",
                                "question": f"Please enter a valid city name for {slot}."
                            }
                        self.state[slot] = city
                        self._reflection_count = 0 
                    else:
                        self.state[slot] = user_query.strip()
                        self.pending_slot = None 

            except Exception:
                return {
                    "status": "NEED_INPUT",
                    "question": f"Invalid value for {slot}. Please try again."
                }

        else:
            if not self._parsed_this_turn:
                self._safe_parse(user_query)
                

        validation = self._validate_current_state()
        if validation:
            return validation

        if (
            self.state == state_snapshot
            and not self.pending_slot
            and not self.pending_outbound_options
            and not self.pending_return_options
            and not getattr(self, "force_finalize", False)   
        ):
            return self._build_fallback_response()

       # ---------- ASK NEXT ----------
        if not getattr(self, "force_finalize", False):
            slot, question = self._missing_slot()
            if slot:
                self.pending_slot = slot
                return {
                    "status": "NEED_INPUT",
                    "question": self._build_reflective_prompt(question)}


        # ---------- OUTBOUND ----------
        travel_date = datetime.fromisoformat(self.state["travel_date"]).date()
        outbound_data = search_flights(self.state["source"], self.state["destination"])
        available_days = outbound_data.get("available_weekdays", [])

        base_price = (
            outbound_data.get("direct_flights", [{}])[0].get("price")
            if outbound_data.get("direct_flights") else None
        )

        if travel_date.strftime("%A").lower() not in available_days:
            candidates = self._outbound_date_candidates(travel_date)
            valid_dates = [d for d in candidates if d.strftime("%A").lower() in available_days]

            #  FORM MODE → FRIENDLY MESSAGE (NO NEED_INPUT)
            if self.force_finalize:
                suggestions = "\n".join(
                    f"• {d.isoformat()} ({d.strftime('%A')})"
                    for d in valid_dates[:3]
                ) or "No nearby available dates."

                return {
                    "status": "FORM_ERROR",
                    "message": (
                        f"❌ **Flights are not available on "
                        f"{travel_date.strftime('%A')} ({travel_date.isoformat()})**\n\n"
                        f"**Nearest available dates:**\n"
                        f"{suggestions}\n\n"
                        f"👉 Please change the travel date in the form and try again."
                    )
                }

            # CHAT MODE → ORIGINAL BEHAVIOR (UNCHANGED)
            self.pending_outbound_options = valid_dates
            return {
                "status": "NEED_INPUT",
                "question": (
                    f"Flights are not available on {self.state['travel_date']}.\n\n" +
                    "\n".join(
                        f"{i+1}) {d.isoformat()}"
                        for i, d in enumerate(valid_dates)
                    ) +
                    "\n\nChoose a number or type 'cancel'."
                )
            }


        outbound_flight = outbound_data.get("direct_flights", [None])[0]

        # ---------- RETURN ----------
        return_flight = None

        if self.state["trip_type"] == "round_trip":
            start = travel_date
            planned_return = start + timedelta(days=self.state["days"] - 1)

            return_data = search_flights(self.state["destination"], self.state["source"])
            #  ROUTE DOES NOT EXIST AT ALL
            if not return_data or not return_data.get("direct_flights"):
                return {
                    "status": "FORM_ERROR" if self.force_finalize else "NEED_INPUT",
                    "message" if self.force_finalize else "question": (
                        "❌ **Return route is not available**.\n\n"
                        f"There are currently no flights from **{self.state['destination']} → {self.state['source']}**.\n\n"
                        "👉 Please switch your trip type to **One Way** to continue."
                    )
                }
            return_days = return_data.get("available_weekdays", [])

            # Return not available on planned date
            if planned_return.strftime("%A").lower() not in return_days:

                #  Try nearby day-count adjustments
                day_offsets = [-3, -2, -1, 1, 2, 3]
                valid_day_options = []

                for offset in day_offsets:
                    new_days = self.state["days"] + offset
                    if new_days <= 1:
                        continue

                    candidate_return = start + timedelta(days=new_days - 1)
                    if candidate_return.strftime("%A").lower() in return_days:
                        valid_day_options.append((new_days, candidate_return))

                #  FORM MODE → FRIENDLY MESSAGE
                if self.force_finalize:
                    suggestions = "\n".join(
                        f"• **{days} days** → return on {d.strftime('%A')} ({d.isoformat()})"
                        for days, d in valid_day_options[:3]
                    ) or "No nearby return options found."

                    return {
                        "status": "FORM_ERROR",
                        "message": (
                            f"❌ **Return flight is not available on "
                            f"{planned_return.strftime('%A')} ({planned_return.isoformat()})**\n\n"
                            f"**Try changing the number of days:**\n"
                            f"{suggestions}\n\n"
                            f"👉 Update the **Number of Days** in the form and try again."
                        )
                    }

                #  CHAT MODE → SHOW NUMBERED RETURN OPTIONS 
                self.pending_return_options = valid_day_options  # keep (days, date)

                return {
                    "status": "NEED_INPUT",
                    "question": (
                        "❌ Return flights are not available for your current trip duration.\n\n"
                        "Here are the nearest available return options:\n"
                        + "\n".join(
                            f"{i+1}) **{days} days** → return on {d.strftime('%A')} ({d.isoformat()})"
                            for i, (days, d) in enumerate(valid_day_options)
                        )
                        + "\n\nChoose a number or type **one-way**."
                    )
                }

            # Return available → proceed
            self.state["return_date"] = planned_return.isoformat()
            self.state["return_resolved"] = True
            return_flight = return_data.get("direct_flights", [None])[0]



            

        if self.state["trip_type"] == "round_trip":
            return_data = search_flights(self.state["destination"], self.state["source"])
            return_flights = return_data.get("direct_flights", [])
            return_flight = return_flights[0] if return_flights else None
        else:
            return_flight = None

        # ---------- FINAL ----------
        hotel = search_hotels(
            self.state["destination"],
            "price_low_to_high" if self.state["preferences"]["budget"] == "budget" else "highest_rated"
        ).get("hotels", [None])[0]

        start_date = travel_date
        end_date = (
            datetime.fromisoformat(self.state["return_date"]).date()
            if self.state["trip_type"] == "round_trip" and self.state["return_date"]
            else start_date + timedelta(days=self.state["days"] - 1)
        )

        try:
            weather = weather_lookup(
                self.state["destination"],
                start_date.isoformat(),
                end_date.isoformat()
            )
        except Exception as e:
            print(f"⚠️ Weather fallback used: {e}")
            weather = {
                "supported": False,
                "city": self.state["destination"],
                "message": f"Weather data is not available for {self.state['destination']}.",
                "daily_forecast": []
            }

        budget = estimate_trip_budget(
        outbound_flight,
        hotel,
        self.state["days"],
        self.state["travelers"],
        return_flight=return_flight,
        budget_tier=self.state["preferences"]["budget"] or "budget"
    )


        raw_places = search_places(self.state["destination"]).get("places", [])
        places = []
        for p in raw_places[:max(self.state["days"] * 2, 3)]:
            p["rating"] = p.get("rating", "N/A")
            places.append(p)

        day_wise_itinerary = self._generate_day_wise_itinerary(
            travel_date,
            self.state["days"],
            hotel,
            raw_places,
            weather,
            outbound_flight=outbound_flight,
            return_flight=return_flight,
        )
        
        self.force_finalize = False

        return {
            "status": "COMPLETED",
            "FINAL_INTENT_JSON": self.state,
            "TRIP_PLAN": {
                "FLIGHT": {
                "outbound": outbound_flight,
                "return": return_flight},
                "HOTEL": hotel,
                "PLACES": raw_places,
                "WEATHER": weather,
                "BUDGET_ESTIMATE": budget,
                "DAY_WISE_ITINERARY": day_wise_itinerary
            }
        }

    # SAFE PARSER

    def _safe_parse(self, user_query: str):
        try:
            extracted = parse_travel_intent(
                self.llm,
                user_query,
                self.state.copy()
            )

            for k, v in extracted.items():
                if v is None:
                    continue

                #  block ONLY true single-city ambiguity
                if k == "destination":
                    if self.state.get("destination") and self.state["destination"] != v:
                        old_dst = self.city_extractor.normalize(self.state["destination"])
                        src = self.city_extractor.normalize(self.state["source"]) if self.state["source"] else None

                        if (
                            not self.city_extractor.is_valid_destination(old_dst)
                            or (src and not self.city_extractor.is_valid_route(src, old_dst))
                        ):
                            self.state["destination"] = v
                            self.pending_slot = None
                        continue

                if self.state.get(k) is not None and k not in ("source", "destination"):
                    continue

                # preferences merge safely
                if k == "preferences" and isinstance(v, dict):
                    for pk, pv in v.items():
                        if self.state["preferences"].get(pk) is None:
                            self.state["preferences"][pk] = pv
                
                else:
                    if k in ("source", "destination"):
                        city = self._extract_city(v)
                        if city:
                            self.state[k] = city
                    else:
                        self.state[k] = v
 

        except Exception as e:
            print("Safe parse error:", e)
