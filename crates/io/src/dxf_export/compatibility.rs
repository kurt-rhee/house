//! Narrow workaround for dxf 0.6.2's missing symbol-table header handles.
//! Entity geometry and serialization remain owned by the dxf crate.
use dxf::Handle;
use std::fmt::Write;

pub(super) fn table_handles(bytes: Vec<u8>, first_free: Handle) -> Result<Vec<u8>, String> {
    let text = String::from_utf8(bytes).map_err(|e| e.to_string())?;
    let lines: Vec<_> = text.lines().collect();
    if !lines.len().is_multiple_of(2) {
        return Err("DXF writer returned incomplete group codes".into());
    }
    let pairs: Vec<_> = lines
        .as_chunks::<2>()
        .0
        .iter()
        .map(|p| {
            let code = p[0].trim().parse::<i32>().map_err(|e| e.to_string())?;
            Ok((code, p[1]))
        })
        .collect::<Result<_, String>>()?;
    let mut insertions = Vec::new();
    for (index, pair) in pairs.iter().enumerate() {
        if *pair != (0, "TABLE") {
            continue;
        }
        if pairs.get(index + 1).map(|p| p.0) != Some(2) {
            return Err("DXF table has no name".into());
        }
        let has_handle = pairs[index + 2..]
            .iter()
            .take_while(|p| p.0 != 0)
            .any(|p| p.0 == 5);
        if !has_handle {
            insertions.push(index + 1);
        }
    }
    // $HANDSEED must remain higher than every entity and newly allocated table handle.
    let next_seed = first_free
        .0
        .checked_add(insertions.len() as u64)
        .ok_or("DXF handle overflow")?;
    let mut next = first_free.0;
    let mut result = String::with_capacity(text.len() + insertions.len() * 32);
    let mut insertion = insertions.into_iter().peekable();
    let mut handseed = false;
    for (index, (code, value)) in pairs.iter().enumerate() {
        if handseed {
            if *code != 5 {
                return Err("DXF HANDSEED has an unexpected group code".into());
            }
            writeln!(result, "  5\n{next_seed:X}").unwrap();
            handseed = false;
        } else {
            writeln!(result, "{code:>3}\n{value}").unwrap();
            handseed = *code == 9 && *value == "$HANDSEED";
        }
        if insertion.peek() == Some(&index) {
            // ROOT owner (0) and the handle precede AcDbSymbolTable subclass data.
            writeln!(result, "  5\n{next:X}\n330\n0").unwrap();
            next += 1;
            insertion.next();
        }
    }
    Ok(result.into_bytes())
}
