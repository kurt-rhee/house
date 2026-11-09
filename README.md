# House

A native, MIT-licensed, local 2D architectural drafting prototype in Rust.
No CAD SDK, account, subscription, cloud service, or AI service is required.
This is the first vertical slice, intended for preliminary residential layouts.
Dimensions are **not construction-ready or verified for building-code compliance**.

## Build and run (macOS)

Install stable Rust and Xcode Command Line Tools, then:

```sh
cargo build --locked --workspace
cargo run --locked -p house-desktop
```

With mise installed, `mise dev` runs the same desktop command.

The app opens a sample bathroom. Save/open use the editable path in the toolbar
(relative to the working directory or absolute). Open replaces the document and
resets history; schema v1 projects migrate automatically to v2 on load. Save uses versioned JSON and an adjacent temporary file plus rename.
**SVG** and **DXF** in the toolbar export beside the project with `.svg` and
`.dxf` extensions. Both export the current committed document without changing
undo history.

- Middle/right drag to pan; scroll over the canvas to zoom about the pointer.
- Click a wall, opening, bath or shower to select it. The inspector edits wall
  endpoints/thickness/name, opening station/width, door type/swing, and fixture
  position/size/rotation. Select a wall to add a centered hinged door, window,
  or sliding glass door; overlapping openings are rejected.
- **Place bath** and **Place shower** place one fixture at the next canvas click.
  Defaults are 60 × 30 inches for baths and 36 × 36 inches for showers; edit exact
  dimensions in the inspector. Rotation is clockwise about the fixture's local
  top-left origin. Escape cancels placement.
- Click **Draw wall**, then two points. Escape cancels. Drawing and dragging snap
  to one-inch increments; property fields accept precise millimeters.
- To move the partition, select the central vertical wall and click **6 in →**.
  Alternatively enter `6 in` and `0` under **Move wall by**. Input accepts decimal
  mm, inches, feet, and feet/inches such as `11' 2"`; fractional-inch notation
  such as `1/2"` is not supported yet.
- Drag a selected wall to translate it. Invalid moves leave the document intact.
- Undo/redo: buttons or ⌘Z / ⌘⇧Z. Both include edits made through MCP.
- **Display inches** changes the measurements shown on the canvas and inspector.
- The checked-in [sample JSON](examples/bathroom.house.json) can also be opened.
  Its [SVG](examples/bathroom.svg) and [DXF](examples/bathroom.dxf) are standalone
  vector drawings.

## Connect MCP to the live application

1. Run `mise dev` (or `cargo run --locked -p house-desktop`). MCP starts
   automatically with the desktop. There is no enable/disable toggle or launch flag.
2. Click **Copy token**. The endpoint is `http://127.0.0.1:3847/mcp`.
   The token changes each time the app launches. The launch terminal also prints
   it. MCP stops when the application quits. If the port is occupied, the app
   shows a persistent MCP startup error.
3. Configure a compatible coding agent for **Streamable HTTP**, with that URL and
   the header `Authorization: Bearer <copied-token>`. For clients using the
   common `mcpServers` configuration shape:

   ```json
   {
     "mcpServers": {
       "house": {
         "type": "http",
         "url": "http://127.0.0.1:3847/mcp",
         "headers": {
           "Authorization": "Bearer <copied-token>"
         }
       }
     }
   }
   ```

   Client configuration field names vary; URL, transport, and header are the
   connection contract. No stdio server starts a separate document.

For Codex, add this entry to `~/.codex/config.toml` (substitute the absolute
path to your checkout):

```toml
[mcp_servers.house]
url = "http://127.0.0.1:3847/mcp"
http_headers_helper = 'python3 "/absolute/path/to/house/scripts/codex-mcp-headers.py"'
```

The desktop publishes its current connection to
`~/Library/Application Support/House/mcp.json`, readable only by your account.
The helper reads that file so there is no token to copy into Codex's configuration.
The token still rotates on every app launch. Keep `mise dev` running; reload MCP
servers or restart Codex after adding the entry. This uses Codex's supported
[HTTP header helper](https://learn.chatgpt.com/docs/extend/mcp#streamable-http-servers).

A small working Rust MCP client is included. To connect and perform the move
without any external agent or service, copy the token and run:

```sh
read -s HOUSE_MCP_TOKEN
export HOUSE_MCP_TOKEN
cargo run --locked -p house-mcp --example move_partition -- '6 in'
cargo run --locked -p house-mcp --example move_partition -- undo
unset HOUSE_MCP_TOKEN
```

The client prints the new revision, room sizes/areas, and dimension values.
Optional `HOUSE_MCP_URL` overrides the endpoint. Leave the desktop running.

An agent given “Move the partition 6 inches to the right” should call
`get_document` or `list_objects`, find the wall named `Partition`, then call:

```json
{"name":"move_wall","arguments":{"id":"<partition UUID>","dx":152.4,"dy":0.0,"expected_revision":0}}
```

Use the revision returned by the read; `0` above applies to an untouched sample.
Create, move, update, and delete tools accept optional `expected_revision`.
A mismatched revision returns a conflict without changing the document or undo
history. Read the current document and reconsider the edit before retrying.
Existing clients can omit the field for an unconditional serialized edit.
The inspector uses this guard automatically when applying object properties,
and the included Rust client supplies it for partition moves.

All tool lengths are millimeters. The app itself does not contain an LLM or
natural-language parser; a compatible agent maps the request to tools.

| Tool | Input |
| --- | --- |
| get_document / list_objects | none; returns semantic objects, revision, derived room/dimension measurements |
| create_wall | name, x1, y1, x2, y2, thickness |
| move_wall | id, dx, dy |
| create_door | wall_id, position (center station), width, swing ("left"/"right") |
| update_door | id, wall_id, position, width, swing; optional kind ("hinged"/"sliding_glass", omitted preserves type) |
| create_sliding_glass_door | wall_id, position (center station), width (total opening) |
| create_window | wall_id, position (center station), width |
| update_window | id, wall_id, position, width |
| create_bath / create_shower | x, y, width, depth; optional rotation (clockwise degrees, defaults to 0) |
| update_fixture | id, x, y, width, depth; optional rotation (defaults to 0) |
| delete_object | id |
| undo / redo | none |
| save_project / export_svg / export_dxf | path |

There are 18 tools. After updating the app, restart House and refresh your agent’s
MCP tool discovery to load the new tools.

Tool validation failures return MCP `isError: true` without committing an edit.
Mutating tools return the committed revision; create tools also return the new ID.
The local token grants editing and local save/export access. The server binds
only to IPv4 loopback, checks the exact Host authority, rejects every present
Origin header, and does not enable CORS. Native/local HTTP clients work; browser
agents need a local native connector rather than a cross-origin browser request.

## Recreating a screenshot with an agent

Attach the screenshot to an image-capable agent connected to House, and give it
at least one measured length (preferably labeled horizontal and vertical dimensions).
The agent can interpret the image, convert the measured layout into millimeters,
and call the semantic creation tools. For example:

> Recreate this bathroom in House. The inside footprint is 134 × 96 inches.
> Use the visible dimensions, add the bath, shower, windows and sliding glass door,
> and ask about dimensions that cannot be read.

House does not run a vision model, accept screenshot uploads, or automatically
trace raster images. Image input belongs to the agent client; MCP carries the
resulting typed edits. The workflow needs a client that can both inspect the
attached image and call MCP tools. Perspective, unlabeled dimensions and obscured
wall edges require interpretation; check the resulting numeric dimensions.
There is no paid service or model dependency inside House.

## DXF export

Click **DXF** in the desktop toolbar, or call the MCP tool:

```json
{"name":"export_dxf","arguments":{"path":"/absolute/path/bathroom.dxf"}}
```

Export writes an ASCII DXF 2007 (AC1021) file at 1:1 scale in **millimeters**.
The app's (x, y) becomes CAD (x, -y), so north points up in CAD without reflecting
the plan's appearance. The export contains real-thickness closed wall outlines
split around door/window openings, door leaf lines and quarter-circle swing arcs,
window frames/glazing, sliding glass panels (without swing arcs), bath/shower
footprints, room names/areas, and dimension lines/ticks/text. Walls, doors,
windows and fixtures use separate CAD layers derived from their source layer name and UUID;
hidden source layers are omitted. Room/dimension annotations follow the desktop's
visibility behavior.

Dimensions are ordinary line/text entities, **not associative CAD DIMENSION
objects**. All exported entities carry their source UUID in HOUSE extended data
for identification, but the DXF is a drawing snapshot, not a parametric project.
Continue using JSON to preserve the editable architectural relationships.
DXF import is not implemented.

The [sample DXF](examples/bathroom.dxf) can be regenerated with the other sample
exports using `cargo run --locked -p house-io --example sample`.

## Bathroom acceptance case

Interior footprint: **3403.6 × 2438.4 mm = 134 × 96 inches**. Exterior wall
inside faces define that footprint; walls are 100 mm thick. The partition
centerline starts at x = 1676.4 mm (66 inches). Room areas exclude wall material.
North is negative Y; positive X is right/east, positive Y down/south.

| Measurement | Initial | Partition +152.4 mm |
| --- | ---: | ---: |
| Partition centerline X | 1676.4 mm | 1828.8 mm |
| Bathroom clear width | 1626.4 mm | 1778.8 mm |
| Utility clear width | 1677.2 mm | 1524.8 mm |
| Both room heights | 2438.4 mm | 2438.4 mm |
| Bathroom area | 3.96581376 m² | 4.33742592 m² |
| Utility area | 4.08968448 m² | 3.71807232 m² |

The two hosted doors, room boundary references, and dimension identities remain
valid. Undo restores every semantic field and coordinate exactly; the live
revision increases to record the undo.

## Checks

```sh
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets -- -D warnings
cargo test --locked --workspace
```

Tests cover geometry, coordinate edits, invalid transactions, exact undo/redo,
JSON float/ID round trips, disk persistence, SVG/DXF output, headless egui mouse
selection/drawing/dragging/zoom, and a real rmcp HTTP client exercising all tools
against the same worker used by the GUI. The HTTP tests also check token, Host,
and Origin rejection, conflicting edits from two clients, and shutting down/restarting
the listener while keeping the document worker alive. DXF tests parse the exported
file and check units, exact wall/dimension coordinates, opening gaps, both door
swings (including diagonal hosts), source IDs, Unicode labels, hidden layers,
failed-write preservation, and live move/undo exports. The sample was also audited
with the independent ezdxf 1.4.5 reader, with no errors or repairs. No screenshot
comparison is required.

## Boundaries of this milestone

Rooms are explicit rectangles referencing axis-aligned wall faces. Moves that
break their enclosure or make them nonpositive are rejected. There is no general
constraint solver, automatic room detection, snapping index, sophisticated wall
join/cleanup, DXF import, PDF, sheets, arbitrary room boundaries,
file picker, recovery/autosave, or native application bundle/installer.
Baths/showers are rectangular plan symbols with no plumbing, clearance checks,
room containment validation or automatic wall attachment. Sliding glass doors
represent two glazed panels; panel handing/operability is not modeled.
Layer visibility is respected by object rendering, SVG, and DXF.

See [architecture](docs/architecture.md) for module boundaries, precision,
transactions, and threading. Current APIs were checked against
[eframe](https://docs.rs/eframe/0.37.0/eframe/) and
[rmcp](https://docs.rs/rmcp/3.9.0/rmcp/) and
[dxf](https://docs.rs/dxf/0.6.2/dxf/); Cargo.lock pins the tested dependencies.

## License

MIT; see [LICENSE](LICENSE).
