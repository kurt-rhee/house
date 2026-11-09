//! Minimal local MCP client, also usable as a reproducible live-app smoke test.
use house_core::parse_length;
use rmcp::{
    ServiceExt,
    model::CallToolRequestParams,
    transport::{
        StreamableHttpClientTransport, streamable_http_client::StreamableHttpClientTransportConfig,
    },
};
use serde_json::{Value, json};
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let token = std::env::var("HOUSE_MCP_TOKEN")
        .map_err(|_| "Set HOUSE_MCP_TOKEN using Copy token in the desktop")?;
    let url = std::env::var("HOUSE_MCP_URL").unwrap_or_else(|_| "http://127.0.0.1:3847/mcp".into());
    let offset = std::env::args().nth(1).unwrap_or_else(|| "6 in".into());
    let transport = StreamableHttpClientTransport::from_config(
        StreamableHttpClientTransportConfig::with_uri(url).auth_header(token),
    );
    let client = ().serve(transport).await?;
    let before = client
        .call_tool(CallToolRequestParams::new("get_document"))
        .await?;
    let d: Value = serde_json::from_str(
        &before.content[0]
            .as_text()
            .ok_or("Expected JSON text")?
            .text,
    )?;
    let wall = d["walls"]
        .as_object()
        .ok_or("No walls")?
        .values()
        .find(|v| v["name"] == "Partition")
        .ok_or("No wall named Partition")?;
    let command = if offset == "undo" {
        CallToolRequestParams::new("undo")
    } else {
        CallToolRequestParams::new("move_wall").with_arguments(serde_json::from_value(
            json!({"id":wall["id"],"dx":parse_length(&offset)?,"dy":0.0,"expected_revision":d["revision"]}),
        )?)
    };
    let result = client.call_tool(command).await?;
    if result.is_error == Some(true) {
        return Err(format!("Edit rejected: {result:?}").into());
    }
    let after = client
        .call_tool(CallToolRequestParams::new("get_document"))
        .await?;
    let d: Value =
        serde_json::from_str(&after.content[0].as_text().ok_or("Expected JSON text")?.text)?;
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"revision":d["revision"],"rooms":d["room_measurements"],"dimensions":d["dimension_measurements"]})
        )?
    );
    client.cancel().await?;
    Ok(())
}
