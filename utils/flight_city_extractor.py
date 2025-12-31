import json
from pathlib import Path


class FlightCityExtractor:
    """
    Single source of truth for:
    - valid cities
    - valid routes
    - city normalization
    - suggestions
    """

    def __init__(self, json_path: str | Path):
        self.json_path = Path(json_path)

        self._sources = set()
        self._destinations = set()
        self._from_to = {}
        self._to_from = {}

        self._load_and_index()

    # Load JSON + build indexes

    def _load_and_index(self):
        if not self.json_path.exists():
            raise FileNotFoundError(f"Flight data not found: {self.json_path}")

        with open(self.json_path, "r", encoding="utf-8") as f:
            flights = json.load(f)

        for f in flights:
            src = f["from"].strip().title()
            dst = f["to"].strip().title()

            self._sources.add(src)
            self._destinations.add(dst)

            self._from_to.setdefault(src, set()).add(dst)
            self._to_from.setdefault(dst, set()).add(src)


    # Normalization
 
    def normalize(self, city: str | None) -> str | None:
        if not city:
            return None
        return city.strip().title()


    # Validation
  
    def is_valid_source(self, city: str) -> bool:
        return self.normalize(city) in self._sources

    def is_valid_destination(self, city: str) -> bool:
        return self.normalize(city) in self._destinations

    def is_valid_route(self, source: str, destination: str) -> bool:
        src = self.normalize(source)
        dst = self.normalize(destination)
        return dst in self._from_to.get(src, set())

 
    # Suggestions
 
    def destinations_from(self, city: str) -> list[str]:
        return sorted(self._from_to.get(self.normalize(city), []))

    def sources_to(self, city: str) -> list[str]:
        return sorted(self._to_from.get(self.normalize(city), []))


    # Public lists

    def all_sources(self) -> list[str]:
        return sorted(self._sources)

    def all_destinations(self) -> list[str]:
        return sorted(self._destinations)
    
    
    import json
from pathlib import Path


class FlightCityExtractor:
    """
    Single source of truth for:
    - valid cities
    - valid routes
    - city normalization
    - suggestions
    """

    def __init__(self, json_path: str | Path):
        self.json_path = Path(json_path)

        self._sources = set()
        self._destinations = set()
        self._from_to = {}
        self._to_from = {}

        self._load_and_index()

    # Load JSON + build indexes

    def _load_and_index(self):
        if not self.json_path.exists():
            raise FileNotFoundError(f"Flight data not found: {self.json_path}")

        with open(self.json_path, "r", encoding="utf-8") as f:
            flights = json.load(f)

        for f in flights:
            src = f["from"].strip().title()
            dst = f["to"].strip().title()

            self._sources.add(src)
            self._destinations.add(dst)

            self._from_to.setdefault(src, set()).add(dst)
            self._to_from.setdefault(dst, set()).add(src)


    # Normalization
 
    def normalize(self, city: str | None) -> str | None:
        if not city:
            return None
        return city.strip().title()


    # Validation
  
    def is_valid_source(self, city: str) -> bool:
        return self.normalize(city) in self._sources

    def is_valid_destination(self, city: str) -> bool:
        return self.normalize(city) in self._destinations

    def is_valid_route(self, source: str, destination: str) -> bool:
        src = self.normalize(source)
        dst = self.normalize(destination)
        return dst in self._from_to.get(src, set())
    
    def is_valid_city(self, city: str | None) -> bool:
        """
        Generic city validation.
        Returns True if city exists as either a source or destination.
        """
        if not city:
            return False
    
        c = self.normalize(city)
        return c in self._sources or c in self._destinations

 
    # Suggestions
 
    def destinations_from(self, city: str) -> list[str]:
        return sorted(self._from_to.get(self.normalize(city), []))

    def sources_to(self, city: str) -> list[str]:
        return sorted(self._to_from.get(self.normalize(city), []))


    # Public lists

    def all_sources(self) -> list[str]:
        return sorted(self._sources)

    def all_destinations(self) -> list[str]:
        return sorted(self._destinations)
    
    
