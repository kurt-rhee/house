//! Real SDK client → loopback HTTP → shared document worker.
use house_core::*;
use house_mcp::*;
use rmcp::{
    ServiceExt,
    model::{CallToolRequestParams, CallToolResult},
    transport::{
        StreamableHttpClientTransport, streamable_http_client::StreamableHttpClientTransportConfig,
    },
};
use serde_json::{Value, json};
use std::sync::{
    Arc,
    atomic::{AtomicUsize, Ordering},
};
fn value(r: CallToolResult) -> Value {
    assert_ne!(r.is_error, Some(true), "{r:?}");
    serde_json::from_str(&r.content[0].as_text().unwrap().text).unwrap()
}
macro_rules! call {
    ($client:expr,$name:expr,$args:expr) => {
        $client
            .call_tool(
                CallToolRequestParams::new($name)
                    .with_arguments(serde_json::from_value($args).unwrap()),
            )
            .await
            .unwrap()
    };
}
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn bathroom_over_real_http() {
    tokio::time::timeout(std::time::Duration::from_secs(30), async {
        let repaints = Arc::new(AtomicUsize::new(0));
        let count = repaints.clone();
        let original = bathroom();
        let partition = original
            .walls
            .values()
            .find(|w| w.name == "Partition")
            .unwrap()
            .id;
        let handle = DocumentHandle::spawn(original.clone(), move || {
            count.fetch_add(1, Ordering::SeqCst);
        })
        .unwrap();
        let server = start_local(handle.clone(), 0).unwrap();
        assert!(server.address.ip().is_loopback());
        let url = format!("http://{}/mcp", server.address);
        let transport = StreamableHttpClientTransport::from_config(
            StreamableHttpClientTransportConfig::with_uri(url.as_str()).auth_header(&server.token),
        );
        let client = ().serve(transport).await.unwrap();
        let tools = client.list_all_tools().await.unwrap();
        assert_eq!(tools.len(), 20);
        let before = value(call!(client, "get_document", json!({})));
        assert_eq!(before["revision"], 0);
        value(call!(client, "list_objects", json!({})));
        value(call!(
            client,
            "move_wall",
            json!({"id":partition,"dx":152.4,"dy":0.0})
        ));
        let after = value(call!(client, "get_document", json!({})));
        assert_eq!(
            handle.snapshot().walls[&partition].start.x,
            original.walls[&partition].start.x + 152.4
        );
        assert_eq!(handle.snapshot().doors, original.doors);
        for r in original.rooms.values() {
            let id = r.id.to_string();
            let old = &before["room_measurements"]
                .as_array()
                .unwrap()
                .iter()
                .find(|v| v["id"] == id)
                .unwrap();
            let new = &after["room_measurements"]
                .as_array()
                .unwrap()
                .iter()
                .find(|v| v["id"] == id)
                .unwrap();
            let delta = if r.east == partition { 152.4 } else { -152.4 };
            assert!(
                (new["width_mm"].as_f64().unwrap() - old["width_mm"].as_f64().unwrap() - delta)
                    .abs()
                    < 1e-9
            );
            assert!(
                (new["area_mm2"].as_f64().unwrap()
                    - old["area_mm2"].as_f64().unwrap()
                    - delta * inches(96.0))
                .abs()
                    < 1e-6
            );
        }
        for dim in original.dimensions.values() {
            let old = house_geometry::dimension_value(&original, dim).unwrap();
            let new = house_geometry::dimension_value(&handle.snapshot(), dim).unwrap();
            match dim.kind {
                DimensionKind::Width => assert!((new - old).abs() > 152.39),
                DimensionKind::Height => assert_eq!(new, old),
            }
        }
        let invalid = call!(
            client,
            "move_wall",
            json!({"id":partition,"dx":10000.0,"dy":0.0})
        );
        assert_eq!(invalid.is_error, Some(true));
        assert_eq!(handle.snapshot().revision, 1);
        value(call!(client, "undo", json!({})));
        let mut restored = (*handle.snapshot()).clone();
        restored.revision = 0;
        assert_eq!(restored, original);
        value(call!(client, "redo", json!({})));
        assert_eq!(handle.snapshot().revision, 3);
        // GUI-style dispatch and MCP dispatch share the same undo history.
        handle
            .request(Action::Edit(house_commands::Command::MoveWall {
                id: partition,
                dx: 25.4,
                dy: 0.0,
            }))
            .await
            .unwrap();
        value(call!(client, "undo", json!({})));
        assert_eq!(
            handle.snapshot().walls[&partition].start.x,
            original.walls[&partition].start.x + 152.4
        );
        let wall = value(call!(
            client,
            "create_wall",
            json!({"name":"Test","x1":5000.0,"y1":0.0,"x2":5000.0,"y2":2500.0,"thickness":100.0})
        ))["id"]
            .as_str()
            .unwrap()
            .to_owned();
        let door = value(call!(
            client,
            "create_door",
            json!({"wall_id":wall,"position":1000.0,"width":700.0,"swing":"left"})
        ))["id"]
            .as_str()
            .unwrap()
            .to_owned();
        value(call!(
            client,
            "update_door",
            json!({"id":door,"wall_id":wall,"position":1100.0,"width":750.0,"swing":"right"})
        ));
        assert_eq!(
            handle.snapshot().doors[&Id::parse_str(&door).unwrap()].position,
            1100.0
        );
        assert_eq!(
            call!(client, "delete_object", json!({"id":wall})).is_error,
            Some(true)
        );
        value(call!(client, "delete_object", json!({"id":door})));
        value(call!(client, "delete_object", json!({"id":wall})));
        let project = std::env::temp_dir().join(format!("house-http-{}.json", Id::new_v4()));
        let svg = project.with_extension("svg");
        value(call!(client, "save_project", json!({"path":project})));
        value(call!(client, "export_svg", json!({"path":svg})));
        assert_eq!(house_io::load(&project).unwrap(), *handle.snapshot());
        assert!(std::fs::read_to_string(&svg).unwrap().contains("<svg"));
        std::fs::remove_file(project).unwrap();
        std::fs::remove_file(svg).unwrap();
        assert!(repaints.load(Ordering::SeqCst) >= 10);
        client.cancel().await.unwrap();
        drop(server);
    })
    .await
    .expect("HTTP workflow timed out");
}
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn rejects_unauthorized_origin_and_host() {
    let handle = DocumentHandle::spawn(bathroom(), || {}).unwrap();
    let server = start_local(handle, 0).unwrap();
    let url = format!("http://{}/mcp", server.address);
    let http = reqwest::Client::new();
    let body = json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1"}}});
    let response = http.post(&url).json(&body).send().await.unwrap();
    assert_eq!(response.status(), 401);
    for (name, header) in [
        ("Origin", "https://untrusted.example"),
        ("Origin", "null"),
        ("Host", "attacker.example"),
    ] {
        let response = http
            .post(&url)
            .bearer_auth(&server.token)
            .header(name, header)
            .header("Accept", "application/json, text/event-stream")
            .json(&body)
            .send()
            .await
            .unwrap();
        assert_eq!(response.status(), 403, "{name}={header}");
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn concurrent_agents_cannot_both_commit_the_same_revision() {
    tokio::time::timeout(std::time::Duration::from_secs(15), async {
        let original = bathroom();
        let id = original
            .walls
            .values()
            .find(|w| w.name == "Partition")
            .unwrap()
            .id;
        let handle = DocumentHandle::spawn(original.clone(), || {}).unwrap();
        let server = start_local(handle.clone(), 0).unwrap();
        let config =
            StreamableHttpClientTransportConfig::with_uri(format!("http://{}/mcp", server.address))
                .auth_header(&server.token);
        let first =
            ().serve(StreamableHttpClientTransport::from_config(config.clone()))
                .await
                .unwrap();
        let second = ().serve(StreamableHttpClientTransport::from_config(config)).await.unwrap();
        let first_read = value(call!(first, "get_document", json!({})));
        let second_read = value(call!(second, "get_document", json!({})));
        assert_eq!(first_read["revision"], second_read["revision"]);
        let params = CallToolRequestParams::new("move_wall").with_arguments(
            serde_json::from_value(json!({"id":id,"dx":152.4,"dy":0.0,"expected_revision":0}))
                .unwrap(),
        );
        let (a, b) = tokio::join!(first.call_tool(params.clone()), second.call_tool(params));
        let (a, b) = (a.unwrap(), b.unwrap());
        assert_eq!(
            [&a, &b].iter().filter(|r| r.is_error == Some(true)).count(),
            1
        );
        let rejected = if a.is_error == Some(true) { a } else { b };
        assert!(
            rejected.content[0]
                .as_text()
                .unwrap()
                .text
                .contains("Revision conflict")
        );
        assert_eq!(handle.snapshot().revision, 1);
        assert_eq!(
            handle.snapshot().walls[&id].start.x,
            original.walls[&id].start.x + 152.4
        );
        // A rejected edit must not add a phantom undo step.
        value(call!(first, "undo", json!({})));
        let mut restored = (*handle.snapshot()).clone();
        restored.revision = 0;
        assert_eq!(restored, original);
        first.cancel().await.unwrap();
        second.cancel().await.unwrap();
    })
    .await
    .expect("Concurrent client workflow timed out");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn shutdown_mcp_with_connected_client_keeps_document_worker_alive() {
    tokio::time::timeout(std::time::Duration::from_secs(10), async {
        let handle = DocumentHandle::spawn(bathroom(), || {}).unwrap();
        let server = start_local(handle.clone(), 0).unwrap();
        let address = server.address;
        let client = ()
            .serve(StreamableHttpClientTransport::from_config(
                StreamableHttpClientTransportConfig::with_uri(format!("http://{address}/mcp"))
                    .auth_header(&server.token),
            ))
            .await
            .unwrap();
        value(call!(client, "get_document", json!({})));
        drop(server);
        // The listener must close even with an initialized client still connected.
        loop {
            match std::net::TcpListener::bind(address) {
                Ok(listener) => {
                    drop(listener);
                    break;
                }
                Err(_) => tokio::time::sleep(std::time::Duration::from_millis(10)).await,
            }
        }
        let before = handle.snapshot();
        let id = before
            .walls
            .values()
            .find(|w| w.name == "Partition")
            .unwrap()
            .id;
        handle
            .request(Action::Edit(house_commands::Command::MoveWall {
                id,
                dx: 152.4,
                dy: 0.0,
            }))
            .await
            .unwrap();
        assert_eq!(
            handle.snapshot().walls[&id].start.x,
            before.walls[&id].start.x + 152.4
        );
        let replacement = start_local(handle.clone(), address.port()).unwrap();
        assert_eq!(replacement.address, address);
        drop(replacement);
        let _ = client.cancel().await;
    })
    .await
    .expect("MCP shutdown did not release its listener or worker");
}

fn assert_dxf_matches_document(path: &std::path::Path, document: &Document) {
    use dxf::entities::EntityType;
    let drawing = dxf::Drawing::load_file(path).unwrap();
    assert_eq!(
        drawing.header.default_drawing_units,
        dxf::enums::Units::Millimeters
    );
    let partition = document
        .walls
        .values()
        .find(|w| w.name == "Partition")
        .unwrap();
    let entity = drawing
        .entities()
        .find(|e| {
            e.common.x_data.iter().any(|data| {
                data.application_name == "HOUSE"
                    && data.items.first() == Some(&dxf::XDataItem::Str(partition.id.to_string()))
            })
        })
        .unwrap();
    let EntityType::LwPolyline(poly) = &entity.specific else {
        panic!("Missing partition polyline")
    };
    for (vertex, expected) in poly
        .vertices
        .iter()
        .zip(house_geometry::wall_polygon(partition))
    {
        assert!((vertex.x - expected.x).abs() < 1e-9);
        assert!((vertex.y + expected.y).abs() < 1e-9);
    }
    for dim in document.dimensions.values() {
        let expected = house_geometry::dimension_value(document, dim).unwrap();
        let label = drawing
            .entities()
            .find_map(|e| {
                let tagged = e.common.x_data.iter().any(|data| {
                    data.application_name == "HOUSE"
                        && data.items.first() == Some(&dxf::XDataItem::Str(dim.id.to_string()))
                });
                match &e.specific {
                    EntityType::Text(t) if tagged => Some(t),
                    _ => None,
                }
            })
            .unwrap();
        assert_eq!(label.value, format!("{expected:.1} mm"));
    }
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn dxf_export_tracks_live_move_and_undo_without_editing_the_document() {
    tokio::time::timeout(std::time::Duration::from_secs(15), async {
        let original = bathroom();
        let partition = original
            .walls
            .values()
            .find(|w| w.name == "Partition")
            .unwrap()
            .id;
        let handle = DocumentHandle::spawn(original.clone(), || {}).unwrap();
        let server = start_local(handle.clone(), 0).unwrap();
        let client = ()
            .serve(StreamableHttpClientTransport::from_config(
                StreamableHttpClientTransportConfig::with_uri(format!(
                    "http://{}/mcp",
                    server.address
                ))
                .auth_header(&server.token),
            ))
            .await
            .unwrap();
        let directory = std::env::temp_dir().join(format!("house-dxf-http-{}", Id::new_v4()));
        std::fs::create_dir(&directory).unwrap();
        let path = directory.join("bathroom.dxf");
        let exported = value(call!(client, "export_dxf", json!({"path":path})));
        assert_eq!(exported["revision"], 0);
        assert_dxf_matches_document(&path, &original);
        value(call!(
            client,
            "move_wall",
            json!({"id":partition,"dx":152.4,"dy":0.0,"expected_revision":0})
        ));
        let moved = handle.snapshot();
        let exported = value(call!(client, "export_dxf", json!({"path":path})));
        assert_eq!(exported["revision"], 1);
        assert_dxf_matches_document(&path, &moved);
        assert_eq!(*handle.snapshot(), *moved);
        value(call!(client, "undo", json!({})));
        let restored = handle.snapshot();
        assert_eq!(restored.walls, original.walls);
        let exported = value(call!(client, "export_dxf", json!({"path":path})));
        assert_eq!(exported["revision"], 2);
        assert_dxf_matches_document(&path, &restored);
        let blocked = directory.join("blocked.dxf");
        std::fs::create_dir(&blocked).unwrap();
        let error = call!(client, "export_dxf", json!({"path":blocked}));
        assert_eq!(error.is_error, Some(true));
        assert_eq!(*handle.snapshot(), *restored);
        assert_eq!(
            std::fs::read_dir(&directory).unwrap().count(),
            2,
            "Failed writes must remove temporary files"
        );
        client.cancel().await.unwrap();
        std::fs::remove_dir_all(directory).unwrap();
    })
    .await
    .expect("DXF export workflow timed out");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn fixtures_windows_and_sliding_doors_through_http() {
    tokio::time::timeout(std::time::Duration::from_secs(20),async {
        let handle=DocumentHandle::spawn(Document::default(),||{}).unwrap();
        let server=start_local(handle.clone(),0).unwrap();
        let client=().serve(StreamableHttpClientTransport::from_config(
            StreamableHttpClientTransportConfig::with_uri(format!("http://{}/mcp",server.address))
                .auth_header(&server.token))).await.unwrap();
        let tools=client.list_all_tools().await.unwrap();
        for name in ["create_bath","create_shower","update_fixture","create_window","update_window","create_sliding_glass_door"] {
            assert!(tools.iter().any(|t| t.name==name));
        }
        let bath=value(call!(client,"create_bath",json!({"x":100.0,"y":200.0,"width":1524.0,"depth":762.0})))["id"].as_str().unwrap().to_owned();
        let shower=value(call!(client,"create_shower",json!({"x":2000.0,"y":200.0,"width":914.4,"depth":914.4,"rotation":90.0})))["id"].as_str().unwrap().to_owned();
        value(call!(client,"update_fixture",json!({"id":bath,"x":252.4,"y":200.0,"width":1600.0,"depth":800.0,"rotation":90.0,"expected_revision":2})));
        let f=&handle.snapshot().fixtures[&Id::parse_str(&bath).unwrap()];
        assert_eq!(f.origin.x,252.4);assert_eq!(f.rotation,90.0);
        let before=handle.snapshot();
        assert_eq!(call!(client,"update_fixture",json!({"id":shower,"x":0.0,"y":0.0,"width":0.0,"depth":900.0})).is_error,Some(true));
        assert_eq!(*handle.snapshot(),*before);
        let wall=value(call!(client,"create_wall",json!({"name":"Glazing","x1":0.0,"y1":0.0,"x2":5000.0,"y2":0.0,"thickness":100.0})))["id"].as_str().unwrap().to_owned();
        let window=value(call!(client,"create_window",json!({"wall_id":wall,"position":1000.0,"width":800.0})))["id"].as_str().unwrap().to_owned();
        let door=value(call!(client,"create_sliding_glass_door",json!({"wall_id":wall,"position":3500.0,"width":1524.0})))["id"].as_str().unwrap().to_owned();
        assert_eq!(handle.snapshot().doors[&Id::parse_str(&door).unwrap()].kind,DoorKind::SlidingGlass);
        value(call!(client,"update_window",json!({"id":window,"wall_id":wall,"position":1100.0,"width":900.0})));
        value(call!(client,"update_door",json!({"id":door,"wall_id":wall,"position":3400.0,"width":1500.0,"swing":"left"})));
        assert_eq!(handle.snapshot().doors[&Id::parse_str(&door).unwrap()].kind,DoorKind::SlidingGlass);
        let before_move=handle.snapshot();
        value(call!(client,"move_wall",json!({"id":wall,"dx":152.4,"dy":25.4})));
        assert_eq!(handle.snapshot().windows,before_move.windows);
        assert_eq!(handle.snapshot().doors,before_move.doors);
        value(call!(client,"undo",json!({})));
        let mut restored=(*handle.snapshot()).clone();restored.revision=before_move.revision;
        assert_eq!(restored,*before_move);
        let before_invalid=handle.snapshot();
        assert_eq!(call!(client,"update_window",json!({"id":window,"wall_id":wall,"position":3400.0,"width":900.0})).is_error,Some(true));
        assert_eq!(*handle.snapshot(),*before_invalid);
        let dir=std::env::temp_dir().join(format!("house-fixtures-{}",Id::new_v4()));
        std::fs::create_dir(&dir).unwrap();
        value(call!(client,"save_project",json!({"path":dir.join("plan.json")})));
        value(call!(client,"export_svg",json!({"path":dir.join("plan.svg")})));
        value(call!(client,"export_dxf",json!({"path":dir.join("plan.dxf")})));
        assert_eq!(house_io::load(&dir.join("plan.json")).unwrap(),*handle.snapshot());
        let svg=std::fs::read_to_string(dir.join("plan.svg")).unwrap();
        for id in [&bath,&shower,&window,&door] {assert!(svg.contains(id));}
        let drawing=dxf::Drawing::load_file(dir.join("plan.dxf")).unwrap();
        for id in [&bath,&shower,&window,&door] {
            assert!(drawing.entities().any(|e| e.common.x_data.iter().any(|data|
                data.items.contains(&dxf::XDataItem::Str(id.to_string())))));
        }
        value(call!(client,"delete_object",json!({"id":shower})));
        assert_eq!(handle.snapshot().fixtures.len(),1);
        value(call!(client,"undo",json!({})));
        assert_eq!(handle.snapshot().fixtures.len(),2);
        std::fs::remove_dir_all(dir).unwrap();
        client.cancel().await.unwrap();
    }).await.expect("Fixture HTTP workflow timed out");
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn named_rooms_over_real_http() {
    tokio::time::timeout(std::time::Duration::from_secs(30), async {
        let original = bathroom();
        let existing = original.rooms.values().next().unwrap().clone();
        let handle = DocumentHandle::spawn(original, || {}).unwrap();
        let server = start_local(handle.clone(), 0).unwrap();
        let config = StreamableHttpClientTransportConfig::with_uri(format!("http://{}/mcp", server.address))
            .auth_header(&server.token);
        let client = ().serve(StreamableHttpClientTransport::from_config(config)).await.unwrap();
        let tools = client.list_all_tools().await.unwrap();
        for name in ["create_room", "rename_room"] {
            assert!(tools.iter().any(|t| t.name == name));
        }
        let name = "Guest bath & <Laundry>";
        value(call!(client, "rename_room", json!({"id":existing.id,"name":name,"expected_revision":0})));
        assert_eq!(handle.snapshot().rooms[&existing.id].name, name);
        assert_eq!(handle.snapshot().dimensions.len(), 4);
        let before = handle.snapshot();
        for args in [
            json!({"id":existing.id,"name":"Stale","expected_revision":0}),
            json!({"id":Id::new_v4(),"name":"Missing"}),
            json!({"id":"invalid","name":"Invalid"}),
        ] {
            assert_eq!(call!(client, "rename_room", args).is_error, Some(true));
            assert_eq!(*handle.snapshot(), *before);
        }
        value(call!(client, "undo", json!({})));
        assert_eq!(handle.snapshot().rooms[&existing.id], existing);
        value(call!(client, "redo", json!({})));
        assert_eq!(handle.snapshot().rooms[&existing.id].name, name);

        // Start with only walls to exercise naming a newly drawn enclosure.
        let mut empty = (*handle.snapshot()).clone();
        empty.rooms.clear();
        empty.dimensions.clear();
        let fresh = DocumentHandle::spawn(empty, || {}).unwrap();
        let fresh_server = start_local(fresh.clone(), 0).unwrap();
        let config = StreamableHttpClientTransportConfig::with_uri(format!("http://{}/mcp", fresh_server.address))
            .auth_header(&fresh_server.token);
        let creator = ().serve(StreamableHttpClientTransport::from_config(config)).await.unwrap();
        let revision = fresh.snapshot().revision;
        let args = json!({"name":name,"west":existing.west,"east":existing.east,"north":existing.north,"south":existing.south,"expected_revision":revision});
        for key in ["west", "north"] {
            let mut invalid = args.clone();
            invalid[key] = json!(existing.south);
            assert_eq!(call!(creator, "create_room", invalid).is_error, Some(true));
            assert_eq!(fresh.snapshot().revision, revision);
            assert!(fresh.snapshot().rooms.is_empty());
        }
        let created = value(call!(creator, "create_room", args));
        let id = Id::parse_str(created["id"].as_str().unwrap()).unwrap();
        assert_eq!(fresh.snapshot().rooms[&id].name, name);
        let described = value(call!(creator, "get_document", json!({})));
        assert_eq!(described["room_measurements"][0]["name"], name);
        value(call!(creator, "undo", json!({})));
        assert!(fresh.snapshot().rooms.is_empty());
        value(call!(creator, "redo", json!({})));
        assert_eq!(fresh.snapshot().rooms[&id].name, name);

        let dir = std::env::temp_dir().join(format!("house-rooms-{}", Id::new_v4()));
        std::fs::create_dir(&dir).unwrap();
        value(call!(creator, "save_project", json!({"path":dir.join("plan.json")})));
        value(call!(creator, "export_svg", json!({"path":dir.join("plan.svg")})));
        value(call!(creator, "export_dxf", json!({"path":dir.join("plan.dxf")})));
        assert_eq!(house_io::load(&dir.join("plan.json")).unwrap(), *fresh.snapshot());
        let svg = std::fs::read_to_string(dir.join("plan.svg")).unwrap();
        assert!(svg.contains("Guest bath &amp; &lt;Laundry&gt;"));
        let drawing = dxf::Drawing::load_file(dir.join("plan.dxf")).unwrap();
        assert!(drawing.entities().any(|e| matches!(&e.specific, dxf::entities::EntityType::Text(t) if t.value == name)));
        value(call!(creator, "delete_object", json!({"id":id})));
        assert!(fresh.snapshot().rooms.is_empty());
        std::fs::remove_dir_all(dir).unwrap();
        creator.cancel().await.unwrap();
        client.cancel().await.unwrap();
    }).await.expect("Room HTTP workflow timed out");
}
