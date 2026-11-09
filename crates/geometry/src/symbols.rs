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
        if matches!(f.kind, FixtureKind::Countertop | FixtureKind::Stove) {
            let mut lines = rectangle(fixture_corners(f));
            if f.kind == FixtureKind::Stove {
                lines.push((
                    transform(f, 0.0, f.depth * 0.12),
                    transform(f, f.width, f.depth * 0.12),
                ));
                for (cx, cy) in [(0.27, 0.36), (0.73, 0.36), (0.27, 0.76), (0.73, 0.76)] {
                    let radius = f.width.min(f.depth) * 0.14;
                    for i in 0..32 {
                        let a = i as f64 * std::f64::consts::TAU / 32.0;
                        let b = (i + 1) as f64 * std::f64::consts::TAU / 32.0;
                        lines.push((
                            transform(
                                f,
                                cx * f.width + radius * a.cos(),
                                cy * f.depth + radius * a.sin(),
                            ),
                            transform(
                                f,
                                cx * f.width + radius * b.cos(),
                                cy * f.depth + radius * b.sin(),
                            ),
                        ));
                    }
                }
            }
            symbols.push(PlanSymbol {
                id: f.id,
                layer: f.layer,
                lines,
            });
            continue;
        }
        if matches!(f.kind, FixtureKind::Toilet | FixtureKind::Sink) {
            let rect = |x1, y1, x2, y2| {
                rectangle([
                    transform(f, x1, y1),
                    transform(f, x2, y1),
                    transform(f, x2, y2),
                    transform(f, x1, y2),
                ])
            };
            let mut lines = if f.kind == FixtureKind::Sink {
                rectangle(fixture_corners(f))
            } else {
                rect(0.0, 0.0, f.width, f.depth * 0.28)
            };
            let (cx, cy, rx, ry) = if f.kind == FixtureKind::Sink {
                (f.width * 0.5, f.depth * 0.55, f.width * 0.32, f.depth * 0.3)
            } else {
                (
                    f.width * 0.5,
                    f.depth * 0.62,
                    f.width * 0.45,
                    f.depth * 0.36,
                )
            };
            for i in 0..32 {
                let a = i as f64 * std::f64::consts::TAU / 32.0;
                let b = (i + 1) as f64 * std::f64::consts::TAU / 32.0;
                lines.push((
                    transform(f, cx + rx * a.cos(), cy + ry * a.sin()),
                    transform(f, cx + rx * b.cos(), cy + ry * b.sin()),
                ));
            }
            if f.kind == FixtureKind::Sink {
                lines.push((transform(f, cx, 0.0), transform(f, cx, f.depth * 0.25)));
            }
            symbols.push(PlanSymbol {
                id: f.id,
                layer: f.layer,
                lines,
            });
            continue;
        }
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
            FixtureKind::Shower
            | FixtureKind::Toilet
            | FixtureKind::Sink
            | FixtureKind::Countertop
            | FixtureKind::Stove => (f.width / 2.0, f.depth / 2.0),
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
        .map(|w| (w.id, w.wall, w.position, w.width, None))
        .chain(
            d.doors
                .values()
                .filter(|v| v.kind != DoorKind::Hinged)
                .map(|v| (v.id, v.wall, v.position, v.width, Some(v.kind))),
        );
    for (id, wall, position, width, kind) in openings {
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
            (p(a, -w.thickness / 2.0), p(a, w.thickness / 2.0)),
            (p(b, -w.thickness / 2.0), p(b, w.thickness / 2.0)),
        ];
        if kind == Some(DoorKind::Pocket) {
            let sign = if d.doors[&id].swing == Swing::Left {
                1.0
            } else {
                -1.0
            };
            let jamb = if sign > 0.0 { b } else { a };
            // A single solid leaf shown half retracted into a dashed wall pocket.
            let leaf_start = jamb - sign * width * 0.5;
            let leaf_end = jamb + sign * width * 0.5;
            lines.extend(rectangle([
                p(leaf_start, -t * 0.55),
                p(leaf_end, -t * 0.55),
                p(leaf_end, t * 0.55),
                p(leaf_start, t * 0.55),
            ]));
            for i in 0..8 {
                let from = jamb + sign * width * i as f64 / 8.0;
                let to = from + sign * width * 0.55 / 8.0;
                for offset in [-t, t] {
                    lines.push((p(from, offset), p(to, offset)));
                }
            }
            let end = jamb + sign * width;
            lines.push((p(end, -t), p(end, t)));
            let arrow_y = -w.thickness / 2.0 - 100.0;
            let tail = position - sign * width * 0.25;
            let tip = position + sign * width * 0.25;
            lines.extend([
                (p(tail, arrow_y), p(tip, arrow_y)),
                (p(tip - sign * 65.0, arrow_y - 35.0), p(tip, arrow_y)),
                (p(tip - sign * 65.0, arrow_y + 35.0), p(tip, arrow_y)),
            ]);
        } else if kind == Some(DoorKind::Garage) {
            // A solid sectional overhead door, distinct from glazed sliding panels.
            let depth = w.thickness * 0.4;
            lines.extend(rectangle([
                p(a, -depth),
                p(b, -depth),
                p(b, depth),
                p(a, depth),
            ]));
            for index in 1..4 {
                let station = a + width * index as f64 / 4.0;
                lines.push((p(station, -depth), p(station, depth)));
            }
            // Short diagonal panel marks indicate solid door leaves rather than glazing.
            for index in 0..4 {
                let middle = a + width * (index as f64 + 0.5) / 4.0;
                lines.push((p(middle - depth, -depth), p(middle + depth, depth)));
            }
        } else if kind == Some(DoorKind::SlidingGlass) {
            // Separate, overlapping panel footprints reveal the two sliding tracks.
            for (left, right, near, far) in [
                (a, position + width * 0.05, -t, -t * 0.3),
                (position - width * 0.05, b, t * 0.3, t),
            ] {
                lines.extend(rectangle([
                    p(left, near),
                    p(right, near),
                    p(right, far),
                    p(left, far),
                ]));
            }
            // A direction arrow beside the wall remains legible at plan scale.
            let arrow_y = -w.thickness / 2.0 - 120.0;
            let tail = position - width * 0.22;
            let tip = position + width * 0.22;
            let head = (width * 0.07).min(140.0);
            lines.extend([
                (p(tail, arrow_y), p(tip, arrow_y)),
                (p(tip - head, arrow_y - head * 0.5), p(tip, arrow_y)),
                (p(tip - head, arrow_y + head * 0.5), p(tip, arrow_y)),
            ]);
        } else {
            for offset in [-t, 0.0, t] {
                lines.push((p(a, offset), p(b, offset)));
            }
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
    fn kitchen_symbols_have_counter_outline_and_four_stove_burners() {
        for (kind, segments) in [(FixtureKind::Countertop, 4), (FixtureKind::Stove, 133)] {
            let mut d = Document::default();
            let f = Fixture {
                id: Id::new_v4(),
                kind,
                origin: Point::new(100.0, 200.0),
                width: 762.0,
                depth: 635.0,
                rotation: 270.0,
                layer: *d.layers.keys().next().unwrap(),
            };
            d.fixtures.insert(f.id, f.clone());
            let symbols = plan_symbols(&d);
            assert_eq!(symbols[0].lines.len(), segments);
            for (a, b) in &symbols[0].lines {
                for p in [a, b] {
                    assert!(p.x >= 100.0 - 0.001 && p.x <= 735.0 + 0.001);
                    assert!(p.y >= -562.0 - 0.001 && p.y <= 200.0 + 0.001);
                }
            }
        }
    }
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
