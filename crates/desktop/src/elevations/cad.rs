use super::Elevation;
use super::svg::{Drawing, Geometry};
use dxf::{
    Color, Drawing as CadDrawing, LwPolylineVertex, Point as CadPoint,
    entities::{Entity, EntityType, Line, LwPolyline, Text},
    enums::{AcadVersion, DrawingUnits, HorizontalTextJustification, Units},
    tables::{Layer, LineType},
};
use eframe::egui::Align;
use kurbo::{Affine, Point, Rect, Shape};
use std::path::Path;

pub(super) fn export(drawing: &Drawing, mm_per_point: f64, path: &Path) -> Result<(), String> {
    let mut cad = CadDrawing::new();
    cad.header.version = AcadVersion::R2007;
    cad.header.default_drawing_units = Units::Millimeters;
    cad.header.drawing_units = DrawingUnits::Metric;
    let bounds = model_bounds(drawing, mm_per_point);
    cad.header.minimum_drawing_extents = CadPoint::new(bounds.x0, bounds.y0, 0.0);
    cad.header.maximum_drawing_extents = CadPoint::new(bounds.x1, bounds.y1, 0.0);
    append(&mut cad, drawing, mm_per_point, "ELEVATION", Point::ORIGIN);
    save(&cad, path)
}

pub(super) fn export_project(
    document: &house_core::Document,
    elevations: &[Elevation],
    path: &Path,
) -> Result<(), String> {
    let mut cad = house_io::plan_dxf_drawing(document)?;
    let gap = 2000.0;
    let left = cad.header.maximum_drawing_extents.x + gap;
    let mut top = cad.header.maximum_drawing_extents.y;
    for row in elevations.chunks(3) {
        let mut x = left;
        let mut bottom = top;
        for elevation in row {
            let scale = elevation.mm_per_point;
            let bounds = model_bounds(&elevation.drawing, scale);
            let origin = Point::new(x - bounds.x0, top - bounds.y1);
            append(&mut cad, &elevation.drawing, scale, &elevation.id, origin);
            cad.header.maximum_drawing_extents.x =
                cad.header.maximum_drawing_extents.x.max(x + bounds.width());
            cad.header.minimum_drawing_extents.y = cad
                .header
                .minimum_drawing_extents
                .y
                .min(top - bounds.height());
            x += bounds.width() + gap;
            bottom = bottom.min(top - bounds.height());
        }
        top = bottom - gap;
    }
    save(&cad, path)
}

fn model_bounds(drawing: &Drawing, mm_per_point: f64) -> Rect {
    let mut bounds = drawing.bounds;
    for object in &drawing.objects {
        let extent = match &object.geometry {
            Geometry::Path(path) => path.bounding_box(),
            Geometry::Text(label) => {
                let width = label.size * label.text.chars().count() as f64;
                let left = match label.anchor {
                    Align::Min => 0.0,
                    Align::Center => -width / 2.0,
                    Align::Max => -width,
                };
                let local = Rect::new(left, -label.size, left + width, label.size / 2.0);
                (Affine::translate(label.baseline.to_vec2()) * Affine::rotate(label.angle))
                    .transform_rect_bbox(local)
            }
        };
        bounds = bounds.union(extent);
    }
    Rect::new(
        (bounds.x0 - drawing.bounds.x0) * mm_per_point,
        (drawing.bounds.y1 - bounds.y1) * mm_per_point,
        (bounds.x1 - drawing.bounds.x0) * mm_per_point,
        (drawing.bounds.y1 - bounds.y0) * mm_per_point,
    )
}

fn save(cad: &CadDrawing, path: &Path) -> Result<(), String> {
    house_io::atomic_write(path, &house_io::serialize_dxf(cad)?)
}

fn append(cad: &mut CadDrawing, drawing: &Drawing, mm_per_point: f64, prefix: &str, origin: Point) {
    let point = |p: Point| {
        CadPoint::new(
            origin.x + (p.x - drawing.bounds.x0) * mm_per_point,
            origin.y + (drawing.bounds.y1 - p.y) * mm_per_point,
            0.0,
        )
    };
    let lines = format!("{prefix}_LINES");
    let fills = format!("{prefix}_FILLS");
    let text = format!("{prefix}_TEXT");
    for (name, color) in [(&lines, 7), (&fills, 8), (&text, 7)] {
        cad.add_layer(Layer {
            name: name.clone(),
            color: Color::from_index(color),
            ..Default::default()
        });
    }
    for object in &drawing.objects {
        match &object.geometry {
            Geometry::Text(label) if object.fill.is_some() && !label.text.is_empty() => {
                let location = point(label.baseline);
                let label = Text {
                    second_alignment_point: location.clone(),
                    location,
                    value: label
                        .text
                        .chars()
                        .map(|c| if c.is_control() { ' ' } else { c })
                        .collect(),
                    text_height: label.size * mm_per_point * 0.72,
                    rotation: -label.angle.to_degrees(),
                    horizontal_text_justification: match label.anchor {
                        Align::Min => HorizontalTextJustification::Left,
                        Align::Center => HorizontalTextJustification::Center,
                        Align::Max => HorizontalTextJustification::Right,
                    },
                    ..Default::default()
                };
                add(cad, EntityType::Text(label), &text, None);
            }
            Geometry::Path(_) if object.stroke.is_some() || object.fill.is_some() => {
                let layer = if object.stroke.is_some() {
                    &lines
                } else {
                    &fills
                };
                let line_type = object
                    .dash
                    .filter(|_| object.stroke.is_some())
                    .map(|[on, off]| {
                        let name = format!("DASH_{on}_{off}");
                        if !cad.line_types().any(|line_type| line_type.name == name) {
                            cad.add_line_type(LineType {
                                name: name.clone(),
                                description: "Elevation dash pattern".into(),
                                element_count: 2,
                                total_pattern_length: f64::from(on + off),
                                dash_dot_space_lengths: vec![f64::from(on), -f64::from(off)],
                                complex_line_type_element_types: vec![0, 0],
                                ..Default::default()
                            });
                        }
                        name
                    });
                for outline in &object.outline {
                    let kind = match outline.as_slice() {
                        [] | [_] => continue,
                        [a, b] => EntityType::Line(Line::new(point(*a), point(*b))),
                        vertices => {
                            let repeated = vertices.first() == vertices.last();
                            let close =
                                repeated || (object.stroke.is_none() && object.fill.is_some());
                            let length = vertices.len() - usize::from(repeated);
                            let mut line = LwPolyline {
                                vertices: vertices[..length]
                                    .iter()
                                    .map(|p| {
                                        let p = point(*p);
                                        LwPolylineVertex {
                                            x: p.x,
                                            y: p.y,
                                            ..Default::default()
                                        }
                                    })
                                    .collect(),
                                ..Default::default()
                            };
                            line.set_is_closed(close);
                            EntityType::LwPolyline(line)
                        }
                    };
                    add(
                        cad,
                        kind,
                        layer,
                        line_type.as_deref().map(|name| (name, mm_per_point)),
                    );
                }
            }
            _ => {}
        }
    }
}

fn add(cad: &mut CadDrawing, geometry: EntityType, layer: &str, line_type: Option<(&str, f64)>) {
    let mut entity = Entity::new(geometry);
    entity.common.layer = layer.into();
    entity.common.transparency = 0x0200_00ff;
    if let Some((line_type, scale)) = line_type {
        entity.common.line_type_name = line_type.into();
        entity.common.line_type_scale = scale;
    }
    cad.add_entity(entity);
}
