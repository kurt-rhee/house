use super::svg::{Drawing, Geometry};
use dxf::{
    Color, Drawing as CadDrawing, LwPolylineVertex, Point as CadPoint,
    entities::{Entity, EntityType, Line, LwPolyline, Text},
    enums::{AcadVersion, DrawingUnits, HorizontalTextJustification, Units},
    tables::{Layer, LineType},
};
use eframe::egui::Align;
use kurbo::Point;
use std::path::Path;

pub(super) fn export(drawing: &Drawing, mm_per_point: f64, path: &Path) -> Result<(), String> {
    let mut cad = CadDrawing::new();
    cad.header.version = AcadVersion::R2007;
    cad.header.default_drawing_units = Units::Millimeters;
    cad.header.drawing_units = DrawingUnits::Metric;
    let point = |p: Point| {
        CadPoint::new(
            (p.x - drawing.bounds.x0) * mm_per_point,
            (drawing.bounds.y1 - p.y) * mm_per_point,
            0.0,
        )
    };
    cad.header.minimum_drawing_extents = CadPoint::origin();
    cad.header.maximum_drawing_extents = point(Point::new(drawing.bounds.x1, drawing.bounds.y0));
    for (name, color) in [
        ("ELEVATION_LINES", 7),
        ("ELEVATION_FILLS", 8),
        ("ELEVATION_TEXT", 7),
    ] {
        cad.add_layer(Layer {
            name: name.into(),
            color: Color::from_index(color),
            ..Default::default()
        });
    }
    for object in &drawing.objects {
        match &object.geometry {
            Geometry::Text(label) if object.fill.is_some() && !label.text.is_empty() => {
                let location = point(label.baseline);
                let text = Text {
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
                add(&mut cad, EntityType::Text(text), "ELEVATION_TEXT", None);
            }
            Geometry::Path(_) if object.stroke.is_some() || object.fill.is_some() => {
                let layer = if object.stroke.is_some() {
                    "ELEVATION_LINES"
                } else {
                    "ELEVATION_FILLS"
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
                                total_pattern_length: f64::from(on + off) * mm_per_point,
                                dash_dot_space_lengths: vec![
                                    f64::from(on) * mm_per_point,
                                    -f64::from(off) * mm_per_point,
                                ],
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
                    add(&mut cad, kind, layer, line_type.as_deref());
                }
            }
            _ => {}
        }
    }
    house_io::atomic_write(path, &house_io::serialize_dxf(&cad)?)
}

fn add(cad: &mut CadDrawing, geometry: EntityType, layer: &str, line_type: Option<&str>) {
    let mut entity = Entity::new(geometry);
    entity.common.layer = layer.into();
    entity.common.transparency = 0x0200_00ff;
    if let Some(line_type) = line_type {
        entity.common.line_type_name = line_type.into();
    }
    cad.add_entity(entity);
}
