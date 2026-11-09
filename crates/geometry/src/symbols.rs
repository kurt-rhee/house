//! Shared plan symbols for desktop, SVG and DXF, derived from semantic objects.
use crate::length;
use house_core::*;

pub struct PlanSymbol {
    pub id: Id,
    pub layer: Id,
    pub lines: Vec<(Point, Point)>,
}
fn transform(f: &Fixture, x: f64, y: f64) -> Point {
    let (sin, cos) = f.rotation.to_radians().sin_cos();
    Point::new(
        f.origin.x + x * cos - y * sin,
        f.origin.y + x * sin + y * cos,
    )
}
pub fn fixture_corners(f: &Fixture) -> [Point; 4] {
    [
        (0.0, 0.0),
        (f.width, 0.0),
        (f.width, f.depth),
        (0.0, f.depth),
    ]
    .map(|(x, y)| transform(f, x, y))
}
pub fn fixture_contains(f: &Fixture, p: Point) -> bool {
    let (sin, cos) = f.rotation.to_radians().sin_cos();
    let dx = p.x - f.origin.x;
    let dy = p.y - f.origin.y;
    let x = dx * cos + dy * sin;
    let y = -dx * sin + dy * cos;
    x >= 0.0 && x <= f.width && y >= 0.0 && y <= f.depth
}
fn rectangle(points: [Point; 4]) -> Vec<(Point, Point)> {
    (0..4).map(|i| (points[i], points[(i + 1) % 4])).collect()
}
pub fn plan_symbols(d: &Document) -> Vec<PlanSymbol> {
    let mut symbols = Vec::new();
    for f in d.fixtures.values() {
        let mut lines = rectangle(fixture_corners(f));
        let inset = f.width.min(f.depth) * 0.08;
        lines.extend(rectangle([
            transform(f, inset, inset),
            transform(f, f.width - inset, inset),
            transform(f, f.width - inset, f.depth - inset),
            transform(f, inset, f.depth - inset),
        ]));
        let drain = match f.kind {
            FixtureKind::Bath => (f.width * 0.85, f.depth / 2.0),
            FixtureKind::Shower => (f.width / 2.0, f.depth / 2.0),
        };
        if f.kind == FixtureKind::Shower {
            for (x, y) in [
                (inset, inset),
                (f.width - inset, inset),
                (f.width - inset, f.depth - inset),
                (inset, f.depth - inset),
            ] {
                lines.push((transform(f, x, y), transform(f, drain.0, drain.1)));
            }
        }
        for (a, b) in [((-15.0, 0.0), (15.0, 0.0)), ((0.0, -15.0), (0.0, 15.0))] {
            lines.push((
                transform(f, drain.0 + a.0, drain.1 + a.1),
                transform(f, drain.0 + b.0, drain.1 + b.1),
            ));
        }
        symbols.push(PlanSymbol {
            id: f.id,
            layer: f.layer,
            lines,
        });
    }
    let openings = d
        .windows
        .values()
        .map(|w| (w.id, w.wall, w.position, w.width, false))
        .chain(
            d.doors
                .values()
                .filter(|v| v.kind == DoorKind::SlidingGlass)
                .map(|v| (v.id, v.wall, v.position, v.width, true)),
        );
    for (id, wall, position, width, sliding) in openings {
        let w = &d.walls[&wall];
        let l = length(w);
        let ux = (w.end.x - w.start.x) / l;
        let uy = (w.end.y - w.start.y) / l;
        let p =
            |x: f64, y: f64| Point::new(w.start.x + ux * x - uy * y, w.start.y + uy * x + ux * y);
        let a = position - width / 2.0;
        let b = position + width / 2.0;
        let t = w.thickness * 0.25;
        let mut lines = vec![
            (p(a, -t), p(b, -t)),
            (p(a, t), p(b, t)),
            (p(a, -w.thickness / 2.0), p(a, w.thickness / 2.0)),
            (p(b, -w.thickness / 2.0), p(b, w.thickness / 2.0)),
        ];
        if sliding {
            // Two overlapping glazed panels; no swing arc.
            lines.push((
                p(position - width * 0.05, -t),
                p(position - width * 0.05, 0.0),
            ));
            lines.push((
                p(position + width * 0.05, 0.0),
                p(position + width * 0.05, t),
            ));
            lines.push((p(a, 0.0), p(b, 0.0)));
        } else {
            lines.push((p(a, 0.0), p(b, 0.0)));
        }
        symbols.push(PlanSymbol {
            id,
            layer: w.layer,
            lines,
        });
    }
    symbols
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rotated_fixture_hit_test_and_symbols_are_derived_without_mutation() {
        let mut d = Document::default();
        let f = Fixture {
            id: Id::new_v4(),
            kind: FixtureKind::Shower,
            origin: Point::new(100.0, 200.0),
            width: 900.0,
            depth: 800.0,
            rotation: 90.0,
            layer: *d.layers.keys().next().unwrap(),
        };
        assert!(fixture_contains(&f, Point::new(-300.0, 650.0)));
        assert!(!fixture_contains(&f, Point::new(300.0, 650.0)));
        d.fixtures.insert(f.id, f.clone());
        let original = d.clone();
        let symbols = plan_symbols(&d);
        assert_eq!(symbols.len(), 1);
        assert_eq!(symbols[0].id, f.id);
        assert_eq!(symbols[0].lines.len(), 14);
        assert_eq!(d, original);
    }
}
