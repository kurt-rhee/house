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
        if matches!(
            f.kind,
            FixtureKind::Countertop
                | FixtureKind::Stove
                | FixtureKind::Refrigerator
                | FixtureKind::ApplianceGarage
        ) {
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
            if f.kind == FixtureKind::ApplianceGarage {
                for y in [0.84, 0.88, 0.92] {
                    lines.push((
                        transform(f, 0.0, f.depth * y),
                        transform(f, f.width, f.depth * y),
                    ));
                }
                lines.push((
                    transform(f, f.width * 0.35, f.depth * 0.96),
                    transform(f, f.width * 0.65, f.depth * 0.96),
                ));
            }
            if f.kind == FixtureKind::Refrigerator {
                let front = f.depth * 0.88;
                lines.push((transform(f, 0.0, front), transform(f, f.width, front)));
                lines.push((
                    transform(f, f.width * 0.5, front),
                    transform(f, f.width * 0.5, f.depth),
                ));
                for x in [0.44, 0.56] {
                    lines.push((
                        transform(f, f.width * x, f.depth * 0.92),
                        transform(f, f.width * x, f.depth * 0.97),
                    ));
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
            | FixtureKind::Stove
            | FixtureKind::Refrigerator
            | FixtureKind::ApplianceGarage => (f.width / 2.0, f.depth / 2.0),
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
        if kind == Some(DoorKind::FrenchGlass) {
            let sign = if d.doors[&id].swing == Swing::Left {
                1.0
            } else {
                -1.0
            };
            let leaf = width / 2.0;
            // Equal leaves at opposite jambs, shown open 90 degrees. Inset parallel
            // lines identify glazing; each swing reaches the shared closed center.
            for (hinge, direction) in [(a, 1.0), (b, -1.0)] {
                lines.extend(rectangle([
                    p(hinge - 18.0, 0.0),
                    p(hinge + 18.0, 0.0),
                    p(hinge + 18.0, sign * leaf),
                    p(hinge - 18.0, sign * leaf),
                ]));
                for offset in [-6.0, 6.0] {
                    lines.push((
                        p(hinge + offset, sign * 60.0),
                        p(hinge + offset, sign * (leaf - 60.0)),
                    ));
                }
                for step in 0..32 {
                    let angle = step as f64 * std::f64::consts::FRAC_PI_2 / 32.0;
                    let next = (step + 1) as f64 * std::f64::consts::FRAC_PI_2 / 32.0;
                    lines.push((
                        p(
                            hinge + direction * leaf * angle.cos(),
                            sign * leaf * angle.sin(),
                        ),
                        p(
                            hinge + direction * leaf * next.cos(),
                            sign * leaf * next.sin(),
                        ),
                    ));
                }
            }
        } else if kind == Some(DoorKind::Pocket) {
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
    fn french_doors_open_both_glazed_leaves_on_selected_side_of_rotated_wall() {
        for swing in [Swing::Left, Swing::Right] {
            let mut d = Document::default();
            let layer = *d.layers.keys().next().unwrap();
            let wall = Wall {
                id: Id::new_v4(),
                name: "Laundry partition".into(),
                start: Point::new(1000.0, 0.0),
                end: Point::new(1000.0, 1800.0),
                thickness: 100.0,
                layer,
            };
            let door = Door {
                id: Id::new_v4(),
                wall: wall.id,
                position: 900.0,
                width: 1200.0,
                swing,
                kind: DoorKind::FrenchGlass,
                hinge_at_end: false,
            };
            d.walls.insert(wall.id, wall);
            d.doors.insert(door.id, door.clone());
            crate::validate(&d).unwrap();
            let symbols = plan_symbols(&d);
            let symbol = symbols.iter().find(|s| s.id == door.id).unwrap();
            let points: Vec<_> = symbol.lines.iter().flat_map(|(a, b)| [a, b]).collect();
            let tip_x = if swing == Swing::Left { 400.0 } else { 1600.0 };
            for y in [300.0, 1500.0] {
                assert!(
                    points
                        .iter()
                        .any(|p| (p.x - tip_x).abs() < 0.001 && (p.y - y).abs() < 0.001)
                );
            }
            // Both arcs reach the closed meeting point, with glazing contained in each leaf.
            assert!(
                points
                    .iter()
                    .any(|p| (p.x - 1000.0).abs() < 0.001 && (p.y - 900.0).abs() < 0.001)
            );
            for p in points {
                assert!(p.y >= 250.0 && p.y <= 1550.0);
                if swing == Swing::Left {
                    assert!(p.x <= 1050.0);
                } else {
                    assert!(p.x >= 950.0);
                }
            }
        }
    }
    #[test]
    fn kitchen_symbols_have_counter_outline_and_four_stove_burners() {
        for (kind, segments) in [
            (FixtureKind::Countertop, 4),
            (FixtureKind::Stove, 133),
            (FixtureKind::Refrigerator, 8),
            (FixtureKind::ApplianceGarage, 8),
        ] {
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
