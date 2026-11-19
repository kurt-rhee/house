use eframe::egui::{self, Color32};
use kurbo::{Affine, BezPath, Circle, PathEl, Point, Rect, Shape, Vec2};
use lyon_tessellation::{
    BuffersBuilder, FillOptions, FillTessellator, FillVertex, VertexBuffers, math::point,
    path::Path,
};
use roxmltree::Node;

pub(super) struct Drawing {
    pub bounds: Rect,
    pub objects: Vec<Object>,
}

pub(super) struct Object {
    pub geometry: Geometry,
    pub fill: Option<Color32>,
    pub stroke: Option<Color32>,
    pub width: f64,
    pub dash: Option<[f32; 2]>,
    pub triangles: VertexBuffers<[f32; 2], u32>,
    pub outline: Vec<Vec<Point>>,
    pub transform_start: usize,
    pub has_transform: bool,
}

pub(super) enum Geometry {
    Path(BezPath),
    Text(Label),
}

pub(super) struct Label {
    pub text: String,
    pub baseline: Point,
    pub size: f64,
    pub angle: f64,
    pub anchor: egui::Align,
    pub bold: bool,
}

impl Drawing {
    pub fn parse(svg: &str) -> Result<Self, String> {
        let document = roxmltree::Document::parse(svg).map_err(|error| error.to_string())?;
        let root = document.root_element();
        if !root.has_tag_name(("http://www.w3.org/2000/svg", "svg")) {
            return Err("Expected an SVG drawing".into());
        }
        let view_box = root
            .attribute("viewBox")
            .ok_or("Elevation SVG needs a viewBox")?
            .parse::<svgtypes::ViewBox>()
            .map_err(|error| error.to_string())?;
        let bounds = Rect::new(
            view_box.x,
            view_box.y,
            view_box.x + view_box.w,
            view_box.y + view_box.h,
        );
        let mut objects = Vec::new();
        for node in root.descendants().skip(1).filter(Node::is_element) {
            let tag = node.tag_name().name();
            if tag == "g" && node.attribute("transform").is_none() {
                continue;
            }
            let number = |name, default| numeric(node.attribute(name), default);
            let transform = node.attribute_node("transform");
            let matrix = match transform {
                Some(attribute) => {
                    let t = attribute
                        .value()
                        .parse::<svgtypes::Transform>()
                        .map_err(|error| error.to_string())?;
                    Affine::new([t.a, t.b, t.c, t.d, t.e, t.f])
                }
                None => Affine::IDENTITY,
            };
            let geometry = match tag {
                "path" => Geometry::Path(
                    matrix
                        * BezPath::from_svg(node.attribute("d").ok_or("Path is missing d")?)
                            .map_err(|error| error.to_string())?,
                ),
                "rect" => {
                    let size = Vec2::new(number("width", 0.0)?, number("height", 0.0)?);
                    let corner = Point::new(number("x", 0.0)?, number("y", 0.0)?);
                    let rect = Rect::from_origin_size(corner, size.to_size());
                    if matrix == Affine::IDENTITY
                        && objects.is_empty()
                        && rect == bounds
                        && node.attribute("fill") == Some("white")
                        && node.attribute("stroke").is_none()
                    {
                        continue;
                    }
                    Geometry::Path(matrix * rect.to_path(0.01))
                }
                "circle" => Geometry::Path(
                    matrix
                        * Circle::new((number("cx", 0.0)?, number("cy", 0.0)?), number("r", 0.0)?)
                            .to_path(0.01),
                ),
                "text" => {
                    let baseline = matrix * Point::new(number("x", 0.0)?, number("y", 0.0)?);
                    let [a, b, ..] = matrix.as_coeffs();
                    Geometry::Text(Label {
                        text: node.text().unwrap_or_default().to_owned(),
                        baseline,
                        size: number("font-size", 16.0)? * a.hypot(b),
                        angle: b.atan2(a),
                        anchor: match inherited(node, "text-anchor") {
                            Some("middle") => egui::Align::Center,
                            Some("end") => egui::Align::Max,
                            _ => egui::Align::Min,
                        },
                        bold: matches!(inherited(node, "font-weight"), Some("bold" | "700")),
                    })
                }
                _ => return Err(format!("Unsupported elevation element <{tag}>")),
            };
            let fill = paint(inherited(node, "fill").unwrap_or("black"))?;
            let stroke = paint(inherited(node, "stroke").unwrap_or("none"))?;
            let width = numeric(inherited(node, "stroke-width"), 1.0)?;
            let dash = inherited(node, "stroke-dasharray")
                .map(|list| -> Result<[f32; 2], String> {
                    let values: Vec<_> = list
                        .split(|c: char| c.is_whitespace() || c == ',')
                        .filter(|value| !value.is_empty())
                        .map(|value| numeric(Some(value), 0.0))
                        .collect::<Result<_, _>>()?;
                    match values.as_slice() {
                        [on, off] if *on > 0.0 && *off > 0.0 => Ok([*on as f32, *off as f32]),
                        _ => Err("Expected two positive dash lengths".into()),
                    }
                })
                .transpose()?;
            let (outline, triangles) = match &geometry {
                Geometry::Path(path) => (outlines(path), fill_mesh(path, fill)?),
                Geometry::Text(_) => (Vec::new(), VertexBuffers::new()),
            };
            objects.push(Object {
                geometry,
                fill,
                stroke,
                width,
                dash,
                triangles,
                outline,
                transform_start: transform.map_or(node.range().start + 1 + tag.len(), |attr| {
                    attr.range_value().start
                }),
                has_transform: transform.is_some(),
            });
        }
        Ok(Self { bounds, objects })
    }
}

fn inherited<'a>(node: Node<'a, '_>, name: &str) -> Option<&'a str> {
    node.ancestors()
        .find_map(|ancestor| ancestor.attribute(name))
}

fn numeric(value: Option<&str>, default: f64) -> Result<f64, String> {
    match value {
        Some(value) => value
            .parse::<f64>()
            .ok()
            .filter(|value| value.is_finite())
            .ok_or_else(|| format!("Invalid drawing coordinate {value}")),
        None => Ok(default),
    }
}

fn paint(value: &str) -> Result<Option<Color32>, String> {
    if value == "none" {
        return Ok(None);
    }
    let color = value
        .parse::<svgtypes::Color>()
        .map_err(|error| error.to_string())?;
    Ok(Some(Color32::from_rgba_unmultiplied(
        color.red,
        color.green,
        color.blue,
        color.alpha,
    )))
}

pub(super) fn outlines(path: &BezPath) -> Vec<Vec<Point>> {
    let mut lines: Vec<Vec<Point>> = Vec::new();
    kurbo::flatten(path, 0.015, |element| match element {
        PathEl::MoveTo(point) => lines.push(vec![point]),
        PathEl::LineTo(point) => lines.last_mut().unwrap().push(point),
        PathEl::ClosePath => {
            let line = lines.last_mut().unwrap();
            if line.first() != line.last() {
                line.push(line[0]);
            }
        }
        _ => unreachable!("flatten only emits straight segments"),
    });
    lines
}

fn fill_mesh(
    path: &BezPath,
    fill: Option<Color32>,
) -> Result<VertexBuffers<[f32; 2], u32>, String> {
    let mut mesh = VertexBuffers::new();
    if fill.is_none() {
        return Ok(mesh);
    }
    let mut builder = Path::builder();
    let mut open = false;
    let pt = |p: Point| point(p.x as f32, p.y as f32);
    for element in path.elements() {
        match *element {
            PathEl::MoveTo(p) => {
                if open {
                    builder.end(false);
                }
                builder.begin(pt(p));
                open = true;
            }
            PathEl::LineTo(p) => {
                builder.line_to(pt(p));
            }
            PathEl::QuadTo(p, q) => {
                builder.quadratic_bezier_to(pt(p), pt(q));
            }
            PathEl::CurveTo(p, q, r) => {
                builder.cubic_bezier_to(pt(p), pt(q), pt(r));
            }
            PathEl::ClosePath => {
                builder.end(true);
                open = false;
            }
        }
    }
    if open {
        builder.end(false);
    }
    FillTessellator::new()
        .tessellate_path(
            &builder.build(),
            &FillOptions::tolerance(0.035).with_fill_rule(lyon_tessellation::FillRule::NonZero),
            &mut BuffersBuilder::new(&mut mesh, |v: FillVertex| v.position().to_array()),
        )
        .map_err(|error| format!("Could not draw SVG fill: {error:?}"))?;
    Ok(mesh)
}
