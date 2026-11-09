//! Deterministic derived geometry; never stored back into semantic objects.
use house_core::*;
use kurbo::{Line, Point as KPoint};
pub fn length(w: &Wall) -> f64 {
    Line::new((w.start.x, w.start.y), (w.end.x, w.end.y)).length()
}
pub fn distance(w: &Wall, p: Point) -> f64 {
    let l = Line::new((w.start.x, w.start.y), (w.end.x, w.end.y));
    l.nearest(KPoint::new(p.x, p.y), 1e-6).distance_sq.sqrt()
}
use kurbo::ParamCurveNearest;
pub fn wall_polygon(w: &Wall) -> [Point; 4] {
    let n = length(w);
    let x = -(w.end.y - w.start.y) / n * w.thickness / 2.0;
    let y = (w.end.x - w.start.x) / n * w.thickness / 2.0;
    [
        Point::new(w.start.x + x, w.start.y + y),
        Point::new(w.end.x + x, w.end.y + y),
        Point::new(w.end.x - x, w.end.y - y),
        Point::new(w.start.x - x, w.start.y - y),
    ]
}
#[derive(Debug, Clone, Copy)]
pub struct Bounds {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
}
impl Bounds {
    pub fn area(&self) -> f64 {
        self.width * self.height
    }
}
pub fn room_bounds(d: &Document, r: &Room) -> Result<Bounds, String> {
    let wall = |id: &Id| d.walls.get(id).ok_or("Missing room boundary".to_string());
    let (w, e, n, s) = (
        wall(&r.west)?,
        wall(&r.east)?,
        wall(&r.north)?,
        wall(&r.south)?,
    );
    if w.start.x != w.end.x || e.start.x != e.end.x || n.start.y != n.end.y || s.start.y != s.end.y
    {
        return Err("Room boundaries must be axis aligned".into());
    }
    let x = w.start.x + w.thickness / 2.0;
    let y = n.start.y + n.thickness / 2.0;
    let right = e.start.x - e.thickness / 2.0;
    let bottom = s.start.y - s.thickness / 2.0;
    if right <= x || bottom <= y {
        return Err("Room must have positive clear size".into());
    }
    for v in [w, e] {
        if v.start.y.min(v.end.y) > y || v.start.y.max(v.end.y) < bottom {
            return Err("Vertical boundary no longer encloses room".into());
        }
    }
    for v in [n, s] {
        if v.start.x.min(v.end.x) > x || v.start.x.max(v.end.x) < right {
            return Err("Horizontal boundary no longer encloses room".into());
        }
    }
    Ok(Bounds {
        x,
        y,
        width: right - x,
        height: bottom - y,
    })
}
pub fn dimension_value(d: &Document, dim: &Dimension) -> Result<f64, String> {
    let b = room_bounds(d, d.rooms.get(&dim.room).ok_or("Missing dimension room")?)?;
    Ok(match dim.kind {
        DimensionKind::Width => b.width,
        DimensionKind::Height => b.height,
    })
}
pub fn validate(d: &Document) -> Result<(), String> {
    if d.layers.is_empty() {
        return Err("At least one layer is required".into());
    }
    if d.schema_version != SCHEMA_VERSION {
        return Err("Unsupported schema version".into());
    }
    let mut ids = std::collections::BTreeSet::new();
    macro_rules! ids {
        ($map:expr) => {
            for (id, obj) in $map {
                if *id != obj.id || !ids.insert(*id) {
                    return Err("Invalid or duplicate object identity".into());
                }
            }
        };
    }
    ids!(&d.walls);
    ids!(&d.doors);
    ids!(&d.windows);
    ids!(&d.fixtures);
    ids!(&d.rooms);
    ids!(&d.room_labels);
    for label in d.room_labels.values() {
        if label.name.trim().is_empty()
            || ![label.position.x, label.position.y]
                .iter()
                .all(|v| v.is_finite() && v.abs() < 1e9)
        {
            return Err("Invalid room label".into());
        }
    }
    ids!(&d.dimensions);
    ids!(&d.layers);
    for w in d.walls.values() {
        if ![w.start.x, w.start.y, w.end.x, w.end.y, w.thickness]
            .iter()
            .all(|n| n.is_finite() && n.abs() < 1e9)
            || length(w) < 0.001
            || w.thickness <= 0.0
            || !d.layers.contains_key(&w.layer)
        {
            return Err("Invalid wall geometry or layer".into());
        }
    }
    for f in d.fixtures.values() {
        if ![f.origin.x, f.origin.y, f.width, f.depth, f.rotation]
            .iter()
            .all(|n| n.is_finite() && n.abs() < 1e9)
            || f.width <= 0.0
            || f.depth <= 0.0
            || !d.layers.contains_key(&f.layer)
        {
            return Err("Invalid fixture geometry or layer".into());
        }
    }
    let mut openings = Vec::new();
    for v in d.doors.values() {
        if v.kind == DoorKind::Pocket {
            let sign = if v.swing == Swing::Left { 1.0 } else { -1.0 };
            // Reserve both the opening and the concealed leaf against other openings.
            openings.push((v.wall, v.position + sign * v.width / 2.0, v.width * 2.0));
        } else {
            openings.push((v.wall, v.position, v.width));
        }
    }
    for v in d.windows.values() {
        openings.push((v.wall, v.position, v.width));
    }
    for (i, (id, p, width)) in openings.iter().enumerate() {
        let w = d.walls.get(id).ok_or("Opening has no host wall")?;
        if !p.is_finite()
            || !width.is_finite()
            || *width <= 0.0
            || p - width / 2.0 < 0.0
            || p + width / 2.0 > length(w)
        {
            return Err("Opening does not fit host wall".into());
        }
        for (other, op, ow) in &openings[..i] {
            if id == other && (p - op).abs() < (width + ow) / 2.0 {
                return Err("Openings overlap".into());
            }
        }
    }
    for r in d.rooms.values() {
        room_bounds(d, r)?;
    }
    for dim in d.dimensions.values() {
        dimension_value(d, dim)?;
    }
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn sample() {
        let d = bathroom();
        validate(&d).unwrap();
        for r in d.rooms.values() {
            assert_eq!(room_bounds(&d, r).unwrap().height, inches(96.0));
        }
        let w = d.walls.values().next().unwrap();
        assert!((distance(w, w.start)).abs() < 1e-9);
        assert_eq!(wall_polygon(w).len(), 4);
    }
}

mod symbols;
pub use symbols::{PlanSymbol, fixture_contains, fixture_corners, plan_symbols};
