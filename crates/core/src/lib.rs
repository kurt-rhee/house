//! Semantic architectural objects. Coordinates and lengths are millimeters.
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
pub use uuid::Uuid as Id;
pub const SCHEMA_VERSION: u32 = 2;
#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}
impl Point {
    pub fn new(x: f64, y: f64) -> Self {
        Self { x, y }
    }
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Wall {
    pub id: Id,
    pub name: String,
    pub start: Point,
    pub end: Point,
    pub thickness: f64,
    pub layer: Id,
}
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
pub enum Swing {
    Left,
    Right,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Serialize, Deserialize)]
pub enum DoorKind {
    #[default]
    Hinged,
    SlidingGlass,
    Garage,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Door {
    pub id: Id,
    pub wall: Id,
    /// Distance from wall start to opening center, in mm.
    pub position: f64,
    pub width: f64,
    pub swing: Swing,
    #[serde(default)]
    pub kind: DoorKind,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Window {
    pub id: Id,
    pub wall: Id,
    pub position: f64,
    pub width: f64,
}
/// Freestanding rectangular footprint; rotation is clockwise degrees about origin.
#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
pub enum FixtureKind {
    Bath,
    Shower,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Fixture {
    pub id: Id,
    pub kind: FixtureKind,
    pub origin: Point,
    pub width: f64,
    pub depth: f64,
    pub rotation: f64,
    pub layer: Id,
}
/// A room name anchored on the plan without implying measured rectangular boundaries.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct RoomLabel {
    pub id: Id,
    pub name: String,
    pub position: Point,
}
/// Rectangular room bounded by the inside faces of axis-aligned walls.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Room {
    pub id: Id,
    pub name: String,
    pub west: Id,
    pub east: Id,
    pub north: Id,
    pub south: Id,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub enum DimensionKind {
    Width,
    Height,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Dimension {
    pub id: Id,
    pub room: Id,
    pub kind: DimensionKind,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Layer {
    pub id: Id,
    pub name: String,
    pub visible: bool,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Document {
    pub schema_version: u32,
    pub revision: u64,
    pub walls: BTreeMap<Id, Wall>,
    pub doors: BTreeMap<Id, Door>,
    pub windows: BTreeMap<Id, Window>,
    #[serde(default)]
    pub fixtures: BTreeMap<Id, Fixture>,
    pub rooms: BTreeMap<Id, Room>,
    #[serde(default)]
    pub room_labels: BTreeMap<Id, RoomLabel>,
    pub dimensions: BTreeMap<Id, Dimension>,
    pub layers: BTreeMap<Id, Layer>,
}
impl Default for Document {
    fn default() -> Self {
        let layer = Layer {
            id: Id::new_v4(),
            name: "Architecture".into(),
            visible: true,
        };
        Self {
            schema_version: SCHEMA_VERSION,
            revision: 0,
            walls: BTreeMap::new(),
            doors: BTreeMap::new(),
            windows: BTreeMap::new(),
            fixtures: BTreeMap::new(),
            rooms: BTreeMap::new(),
            room_labels: BTreeMap::new(),
            dimensions: BTreeMap::new(),
            layers: BTreeMap::from([(layer.id, layer)]),
        }
    }
}
pub fn inches(value: f64) -> f64 {
    value * 127.0 / 5.0
}
/// Accept mm, decimal inches, feet, and feet/inches such as 11' 2".
pub fn parse_length(text: &str) -> Result<f64, String> {
    let s = text.trim();
    let number = |n: &str| n.trim().parse::<f64>().map_err(|e| e.to_string());
    let value = if let Some((feet, rest)) = s.split_once('\'') {
        let tail = rest.trim().trim_end_matches('"').trim();
        let feet = number(feet)?;
        let inch = if tail.is_empty() { 0.0 } else { number(tail)? };
        if inch < 0.0 || inch >= 12.0 {
            return Err("Feet/inches remainder must be between 0 and 12".into());
        }
        inches(if feet < 0.0 {
            feet * 12.0 - inch
        } else {
            feet * 12.0 + inch
        })
    } else {
        let (n, factor) = if let Some(n) = s.strip_suffix("mm") {
            (n, 1.0)
        } else if let Some(n) = s.strip_suffix("in").or_else(|| s.strip_suffix('"')) {
            (n, 25.4)
        } else if let Some(n) = s.strip_suffix("ft") {
            (n, 304.8)
        } else {
            (s, 1.0)
        };
        if factor == 25.4 {
            inches(number(n)?)
        } else if factor == 304.8 {
            inches(number(n)? * 12.0)
        } else {
            number(n)?
        }
    };
    if !value.is_finite() {
        return Err("Length must be finite".into());
    }
    Ok(value)
}
pub fn bathroom() -> Document {
    let mut d = Document::default();
    let layer = *d.layers.keys().next().unwrap();
    let t = 100.0;
    let w = inches(134.0);
    let h = inches(96.0);
    let p = inches(66.0);
    let mut wall = |name: &str, a: Point, b: Point| {
        let id = Id::new_v4();
        d.walls.insert(
            id,
            Wall {
                id,
                name: name.into(),
                start: a,
                end: b,
                thickness: t,
                layer,
            },
        );
        id
    };
    let west = wall(
        "West",
        Point::new(-t / 2.0, -t / 2.0),
        Point::new(-t / 2.0, h + t / 2.0),
    );
    let east = wall(
        "East",
        Point::new(w + t / 2.0, -t / 2.0),
        Point::new(w + t / 2.0, h + t / 2.0),
    );
    let north = wall(
        "North",
        Point::new(-t / 2.0, -t / 2.0),
        Point::new(w + t / 2.0, -t / 2.0),
    );
    let south = wall(
        "South",
        Point::new(-t / 2.0, h + t / 2.0),
        Point::new(w + t / 2.0, h + t / 2.0),
    );
    let partition = wall(
        "Partition",
        Point::new(p, -t / 2.0),
        Point::new(p, h + t / 2.0),
    );
    for (name, west, east) in [("Bathroom", west, partition), ("Utility", partition, east)] {
        let id = Id::new_v4();
        d.rooms.insert(
            id,
            Room {
                id,
                name: name.into(),
                west,
                east,
                north,
                south,
            },
        );
        for kind in [DimensionKind::Width, DimensionKind::Height] {
            let dim = Dimension {
                id: Id::new_v4(),
                room: id,
                kind,
            };
            d.dimensions.insert(dim.id, dim);
        }
    }
    for (wall, position) in [
        (west, inches(48.0) + t / 2.0),
        (north, inches(108.0) + t / 2.0),
    ] {
        let door = Door {
            id: Id::new_v4(),
            wall,
            position,
            width: inches(28.0),
            kind: DoorKind::Hinged,
            swing: if wall == west {
                Swing::Right
            } else {
                Swing::Left
            },
        };
        d.doors.insert(door.id, door);
    }
    d
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn units() {
        assert_eq!(parse_length("6 in").unwrap(), 152.4);
        assert_eq!(parse_length("-1' 2\"").unwrap(), -inches(14.0));
        for invalid in ["NaN", "inf", "11' nope", "2' 14\"", ""] {
            assert!(parse_length(invalid).is_err(), "{invalid}");
        }
        assert_eq!(parse_length("11' 2\"").unwrap(), inches(134.0));
    }
}
