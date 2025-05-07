class GolfCourse:
  def __init__(self, id, name, lat, lon, source):
    self.id = id
    self.name = name
    self.lat = lat
    self.lon = lon
    self.source = source

  def to_dict(self):
    return {
      "id": self.id,
      "name": self.name,
      "lat": self.lat,
      "lon": self.lon,
      "source": self.source
    }

  def __repr__(self):
    return f"GolfCourse(name={self.name}, lat={self.lat}, lon={self.lon})"