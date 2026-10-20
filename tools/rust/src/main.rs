// rare (Rust) - a small CLI over data/resources.json.
//
// Part of the n-of-1-resources polyglot toolkit. Reads the same JSON dataset
// as the Python and Go tools and produces the same style of output.
//
// Build:  cargo build --release --manifest-path tools/rust/Cargo.toml
// Run:    ./tools/rust/target/release/rare list
//         ./tools/rust/target/release/rare search aso
//         ./tools/rust/target/release/rare cat treatment
//
// Data path: defaults to data/resources.json, or set RARE_DATA to override.

use serde::Deserialize;
use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::path::Path;
use std::process::exit;

const VALID_CATEGORIES: [&str; 4] = ["community", "registry", "treatment", "reference"];

#[derive(Deserialize)]
struct Resource {
    id: String,
    name: String,
    category: String,
    region: String,
    url: String,
    #[serde(default)]
    audience: Vec<String>,
    #[serde(default)]
    tags: Vec<String>,
    description: String,
}

#[derive(Deserialize)]
struct Dataset {
    #[serde(default)]
    resources: Vec<Resource>,
}

fn is_valid_category(c: &str) -> bool {
    VALID_CATEGORIES.contains(&c)
}

fn data_path() -> String {
    if let Ok(p) = env::var("RARE_DATA") {
        if !p.is_empty() {
            return p;
        }
    }
    for candidate in [
        "data/resources.json",
        "../../data/resources.json",
        "../../../data/resources.json",
    ] {
        if Path::new(candidate).exists() {
            return candidate.to_string();
        }
    }
    "data/resources.json".to_string()
}

fn load(path: &str) -> Result<Vec<Resource>, String> {
    let raw = fs::read_to_string(path).map_err(|e| format!("cannot read {}: {}", path, e))?;
    let ds: Dataset =
        serde_json::from_str(&raw).map_err(|e| format!("invalid JSON in {}: {}", path, e))?;
    Ok(ds.resources)
}

fn matches(r: &Resource, query: &str) -> bool {
    let hay = format!(
        "{} {} {} {} {} {}",
        r.name,
        r.description,
        r.category,
        r.region,
        r.tags.join(" "),
        r.audience.join(" ")
    )
    .to_lowercase();
    hay.contains(&query.to_lowercase())
}

fn print_rows(rows: &[&Resource]) {
    for r in rows {
        println!("[{:<9}] {:<44} {}", r.category, r.name, r.url);
    }
    println!("\n{} resource(s)", rows.len());
}

fn cmd_stats(rows: &[Resource]) {
    let mut cats: BTreeMap<&str, usize> = BTreeMap::new();
    let mut regions: BTreeMap<&str, usize> = BTreeMap::new();
    for r in rows {
        *cats.entry(r.category.as_str()).or_insert(0) += 1;
        *regions.entry(r.region.as_str()).or_insert(0) += 1;
    }
    println!("total: {}\n\nby category:", rows.len());
    for c in VALID_CATEGORIES {
        if let Some(n) = cats.get(c) {
            println!("  {:<10} {}", c, n);
        }
    }
    println!("\nby region:");
    for (k, n) in &regions {
        println!("  {:<10} {}", k, n);
    }
}

fn cmd_validate(rows: &[Resource]) -> i32 {
    let mut problems: Vec<String> = Vec::new();
    let mut seen: Vec<&str> = Vec::new();
    for r in rows {
        if r.id.is_empty() {
            problems.push("resource with empty id".to_string());
        } else if seen.contains(&r.id.as_str()) {
            problems.push(format!("duplicate id '{}'", r.id));
        } else {
            seen.push(r.id.as_str());
        }
        if !is_valid_category(&r.category) {
            problems.push(format!("{}: invalid category '{}'", r.id, r.category));
        }
        if !r.url.starts_with("http") {
            problems.push(format!("{}: url does not start with http", r.id));
        }
        if r.name.is_empty() || r.description.is_empty() || r.region.is_empty() {
            problems.push(format!("{}: missing name/description/region", r.id));
        }
    }
    if !problems.is_empty() {
        println!("INVALID - {} problem(s):", problems.len());
        for p in &problems {
            println!("  - {}", p);
        }
        return 1;
    }
    println!(
        "OK - {} resources, all ids unique, categories/urls valid",
        rows.len()
    );
    0
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("usage: rare <list|search <q>|cat <category>|stats|validate>");
        exit(2);
    }

    let rows = match load(&data_path()) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("{}", e);
            exit(1);
        }
    };

    match args[0].as_str() {
        "list" => {
            let refs: Vec<&Resource> = rows.iter().collect();
            print_rows(&refs);
        }
        "search" => {
            if args.len() < 2 {
                eprintln!("search needs a query");
                exit(2);
            }
            let q = args[1..].join(" ");
            let refs: Vec<&Resource> = rows.iter().filter(|r| matches(r, &q)).collect();
            print_rows(&refs);
        }
        "cat" => {
            if args.len() < 2 || !is_valid_category(&args[1]) {
                eprintln!("cat needs one of: community, registry, treatment, reference");
                exit(2);
            }
            let refs: Vec<&Resource> = rows.iter().filter(|r| r.category == args[1]).collect();
            print_rows(&refs);
        }
        "stats" => cmd_stats(&rows),
        "validate" => exit(cmd_validate(&rows)),
        other => {
            eprintln!("unknown command '{}'", other);
            exit(2);
        }
    }
}
