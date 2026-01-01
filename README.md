# ✈️ Agentic_AI_Based_Travel_Planning_Assistant

A production-grade **Agentic AI system** that plans complete trips end-to-end — including flights, hotels, weather, budget estimation, and a day-wise itinerary — using **stateful reasoning, tool orchestration, and availability-aware decision making**.

The system plans:
- Flights (one-way / round-trip)
- Hotels
- Places to visit
- Weather forecasts (Using Open-Meteo)
- Budget breakdown (total + per person)
- Day-wise itinerary
- Downloadable PDF summary


---
---

## 🚀 Key Highlights

- True agentic AI architecture
- Stateful slot-filling & intent control
- Availability-aware flight planning
- Smart round-trip & date resolution
- Budget breakdown (total + per person)
- Weather-aware itinerary generation
- Streamlit UI with glassmorphism design
- Local LLM + Hugging Face API support
- One-click PDF trip export
- Supports local LLMs (Phi-3, Qwen 2.5) (For fallback if HuggingFace API doesn't worked)

---
---

## 📁 Project Structure

  ```
  Agentic_AI_Based_Travel_Planning_Assistant/
  │
  ├── agent/
  │   ├── __init__.py
  │   ├── intent_manager.py
  │   ├── intent_parser.py
  │   ├── llm_loader.py
  │   └── travel_agent.py
  │
  ├── assets/
  │   └── styles.css
  │
  ├── data/
  │   ├── flights.json
  │   ├── hotels.json
  │   └── places.json
  │
  ├── llm_models/
  │   ├── phi-3-mini-4k-instruct-q4.gguf
  │   ├── qwen2.5-3b-instruct-q4_k_m.gguf
  │
  ├── pdf/
  │   └── trip_pdf_generator.py
  │
  ├── tools/
  │   ├── budget_tool.py
  │   ├── flight_tool.py
  │   ├── hotel_tool.py
  │   ├── places_tool.py
  │   └── weather_lookup_tool.py
  │
  ├── utils/
  │   ├── flight_city_extractor.py
  │   └── helpers.py
  │
  ├── streamlit_app.py
  ├── requirements.txt
  └── README.md
  ```

---
---

## ⚙️ Installation & Setup ( Step by Step)

### 1. Clone the Repository

```
git clone https://github.com/Predeep-Kumar/Agentic_AI_Based_Travel_Planning_Assistant.git
```

```
cd Agentic_AI_Based_Travel_Planning_Assistant
```

### 2. Create Virtual Environment

1. Creating
  ```
  py -m venv venv
  ```

or

  ```
  python -m venv venv
  ```
or 
  ```
  python3 -m venv venv
  ```

2. Activating The enviroment

  For macOS / Linux
  ```
  source venv/bin/activate 
  ```
  For Windows
  ```
  venv\Scripts\activate     
  ```

### 3. Install Requirements

  ```
  pip install -r requirements.txt
  ```

### 4. Set the environment variable (in .env file):

  ```HUGGINGFACE_API_KEY=your_api_key_here```

### 5. Download LLM Models (Important for fallback)

  Place downloaded .gguf files inside folder:
  
  ``` llm_models/ ```
  
  How to Download ( use below code in terminal)
  
  1. Phi-3 Mini
  
  For Windows
  ```
  curl.exe -L https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf -o llm_models/phi-3-mini-4k-instruct-q4.gguf
  ```
  
  For macOS / Linux 
  ```
  curl -L https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf -o llm_models/phi-3-mini-4k-instruct-q4.gguf
  ```
  
  3. Qwen 2.5 (Better Reasoning)
  
  For Windows
  ```
  curl.exe -L https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf -o llm_models/qwen2.5-3b-instruct-q4_k_m.gguf
  ```
  
  For macOS / Linux 
  ```
  curl -L https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf -o llm_models/qwen2.5-3b-instruct-q4_k_m.gguf  
  ```


### 6. Run the Application

  ```
  python -m streamlit run streamlit_app.py
  ```

---
---


 ## 🧠 System Architecture (High Level)

  The system follows an **agent + tools** workflow:
  
  ```
  User Input
  ↓
  Intent Gating
  ↓
  Stateful Slot Filling
  ↓
  Validation & Availability Checks
  ↓
  Tool Execution (Flights / Hotels / Weather / Budget)
  ↓
  Reasoned Final Plan
  ↓
  UI Rendering + PDF Export
  ```
  
  The agent **finalizes only when all constraints are valid**.

---
---

## Agent (TravelAgent) –  🧩 Core Features

  ### 1. Intent Gating
  
  The agent begins trip planning only when intent is clear.
  
  Trigger keywords: plan, trip, travel, vacation, holiday, tour.
  
  This prevents random or irrelevant inputs from breaking the flow.
  
  
  ### 2. Stateful Slot Management (Session-Based)
  
  The agent maintains a structured session state:
  
  - Source city
  - Destination city
  - Trip type (one-way / round-trip)
  - Travel date
  - Return date
  - Number of days
  - Number of travelers
  - Budget preference
  - Optional interests
  
  All data lives **only in the current session**  
  (no long-term memory or vector database used).
  
  
  ### 3. Slot-by-Slot Question Engine
  
  The agent automatically asks only missing information, in order:
  
  1. Source
  2. Destination
  3. Trip type
  4. Travel date
  5. Number of days
  6. Travelers
  7. Budget preference
  
  No duplicate or unnecessary questions.
  
  
  
  ### 4. Natural Language Parsing (LLM-Assisted)
  
  Free-text input is parsed using an LLM:
  
  - Extracts cities from natural language
  - Understands multi-slot sentences
  - Safely merges new data into state
  - Prevents overwriting confirmed slots
  
  
  
  ### 5. Global Cancel & Restart
  
  At any point, the user can type: 
  ``` cancel ```
  Behavior:
  - Clears agent state
  - Removes pending options
  - Allows a clean restart

---
---

## Tooling Layer

  ### ✈️ Flight Tool
  
  ```search_flights(source, destination)```
  
  Returns:
  
  - Direct flights
  - Airline
  - Price
  - Duration
  - Departure / arrival time
  - Cheapest / fastest flags
  - Available weekdays
  
  Availability-Aware Planning:
  
  - Validates selected travel date
  - Suggests nearest valid dates if unavailable
  - Handles historical weekday availability
  
  Round-Trip Logic:
  
  - Validates return flight availability
  - Suggests alternate durations
  - Allows switching to one-way when required
  
   
   ### 🏨 Hotel Tool
  
    ```search_hotels(destination, sort_by)```
  
  Selection logic:
  
  - Budget → lowest price
  - Mid / luxury → highest rated
  
  Returns:
  
  - Hotel name
  - Price per night
  - Rating
  - Location
  - Amenities
  
  
   ### 📍 Places Tool
  
  ``` search_places(destination)```
  
  Returns:
  
  - Tourist attractions
  - Place types
  - Ratings
  
  Agent logic:
  
  - Recommends max(days × 2, 3) places
  - Ensures full itinerary coverage
  
  
  ### 🌦 Weather Tool
  
  ```weather_lookup(destination, start_date, end_date)```
  
  Provides:
  
  - Daily forecast
  - Conditions
  - Min / max temperature
  - Rain probability
  - Comfort index
  - Used in UI and itinerary narration.
  
  
  ### 💰 Budget Tool
  
  ``` estimate_trip_budget(
      outbound_flight,
      hotel,
      days,
      travelers,
      return_flight=None
  )
  ```
  
  Calculates:
  
  - Flight cost
  - Hotel cost
  - Food, local travel and miscellaneous
  - Per-person cost
  - Total estimated budget

---
---

## Streamlit UI Features

  ### 💬 Chat Mode
  
  - Conversational interface
  - Streaming response animation
  - Session-based interaction
  
  ### 📝 Form Mode
  
  - Structured trip input
  - Same agent logic as chat mode
  - Validation before execution
  
  ### 🎨 Design System
 
  - iOS-style glassmorphism
  - Blur + gradient cards
  - Hover animations
  - Responsive layout

  ### 📄 PDF Export
  
  - One-click downloadable trip PDF
  - Includes Trip overview, full daywise itinerary & budget
  
  ### 🖥 Final Output
  
  - Trip overview
  - Flights
  - Hotel details
  - Places to visit
  - Weather forecast
  - Budget breakdown
  - Day-wise itinerary
  - PDF download
  
  ---
  ---

## 🤖 Models Details

  ### Local LLM Support
  
  This project supports local GGUF models using llama.cpp.
  
  1. Phi-3 Mini 
  2. Qwen 2.5 
  
  ### Hugging Face API 
  
  we are using ```Mistral-7B-Instruct-v0.2```
  
  We need this API to call the model online from Hugging Face. If it’s not available, the system won’t be able to fetch the model from Hugging Face and will fall back to using the locally downloaded models instead.
  
  1. Create an account on Hugging Face
  2. Generate an API token
  3. Set the environment variable (in .env file):
  
  ```HUGGINGFACE_API_KEY=your_api_key_here```
  
  The app automatically switches between API → local fallback when needed.

---
---


## ✅ What Makes This Project Stand Out

- ✔️ True Agentic AI (not prompt-based)
- ✔️ Tool-driven reasoning
- ✔️ Availability-aware planning
- ✔️ Stateful control flow
- ✔️ Graceful cancellation & recovery
- ✔️ Robust error handling
- ✔️ Real-world constraints handled correctly
- ✔️ Production-ready and Clean UI & UX
- ✔️ Modular & extensible design

---
---

## 📌 Ideal Use Cases

- AI travel assistants
- Agentic AI demos
- Trip planning platforms
- Portfolio projects &  case study
- SaaS foundations
- Intelligent planning systems

---
---

## 🚀 Future Scope & Enhancements (Idea-Level)

- 1️⃣ Multi-City Trip Planning
Extend the planner to support trips covering multiple cities in one journey, allowing users to plan complex itineraries instead of a single destination.

- 2️⃣ Expanded Travel Data Coverage
Increase the number of supported cities, routes, hotels, and attractions to make trip plans more realistic and diverse.

- 3️⃣ Smarter Preference-Based Planning
Allow users to specify travel styles such as adventure, relaxation, family trips, nightlife, or food-focused journeys to receive more personalized plans.

- 4️⃣ More Intelligent Conversational Experience
Improve the AI’s conversational abilities so it can ask better follow-up questions, clarify user intent, and provide more natural responses.

- 5️⃣ Flexible Date Suggestions
Enable the system to suggest better travel dates based on availability, affordability, or convenience instead of fixed user-selected dates.

- 6️⃣ Advanced Budget Customization
Allow users to explore multiple budget scenarios and compare different comfort levels within the same trip plan.

- 7️⃣ Weather-Aware Planning
Adapt itineraries dynamically based on expected weather conditions to improve comfort and safety during travel.

- 8️⃣ Packing & Travel Preparation Assistance
Provide intelligent packing suggestions based on destination, trip duration, and expected activities.

- 9️⃣ Enhanced User Interface & Visual Experience
Further improve the UI with richer visuals, smoother animations, and a more immersive travel-planning experience. Aso add ing Auto and smooth scrolling.

- 🔟 Interactive Maps & Route Visualization
Visualize routes, destinations, hotels, and attractions on interactive maps to give users a clearer understanding of their journey.

- 1️⃣1️⃣ Trip Comparison & What-If Scenarios
Allow users to compare multiple trip options or modify plans to instantly see how changes affect the overall journey.

- 1️⃣2️⃣ Shareable & Editable Trip Plans
Enable users to share trip plans easily or export them in more customizable formats.

- 1️⃣3️⃣ User Profiles & Trip History
Allow users to save trips, revisit previous plans, and build a personal travel history.

- 1️⃣4️⃣ Confidence & Explanation Layer
Provide simple explanations for recommendations to help users understand why specific options were chosen.

- 1️⃣5️⃣ Continuous Intelligence Improvement
Gradually enhance the AI’s reasoning capabilities to make trip planning more accurate, flexible, and user-friendly. Also adding Fuzzy spelling check.

---
---

## 🏁 Conclusion

This project demonstrates the successful design and implementation of an Agentic AI–based Travel Planning Assistant capable of transforming natural user input into a complete, structured, and actionable trip plan. Unlike traditional rule-based or static chatbots, the system operates as a state-aware decision-making agent that intelligently guides users through the travel planning process.

The assistant is able to understand user intent, manage conversation flow, validate inputs, and dynamically interact with multiple domain-specific tools to generate realistic travel outputs. By combining flight availability checks, hotel selection, destination recommendations, weather forecasting, and budget estimation, the system delivers an end-to-end travel planning experience within a single unified interface.

A strong emphasis was placed on user experience and reliability. The application gracefully handles incomplete inputs, unavailable travel dates, invalid routes, and mid-conversation cancellations, ensuring a smooth and intuitive interaction flow. The Streamlit-based interface further enhances usability through a clean, modern glassmorphism design and structured result presentation.

Overall, this project highlights the practical application of agent-based AI systems in real-world scenarios. It demonstrates how intelligent agents, when paired with modular tools and thoughtful UI design, can move beyond simple question–answer systems and deliver meaningful, decision-oriented outcomes. The architecture is modular, extensible, and well-positioned for future enhancements such as multi-city planning, richer datasets, and deeper personalization.

This work serves as a strong foundation for building scalable, intelligent travel planning platforms and showcases the potential of agentic AI in solving complex, real-life planning problems.
 

## 🤝 Author

### **Predeep Kumar** 

🧑‍💻 AI Engineer | Agentic AI Systems | Applied Machine Learning  

Built with ❤️ as an advanced **Agentic AI Travel Planning Assistant**, demonstrating real-world AI orchestration, reasoning, and user-centric system design.
