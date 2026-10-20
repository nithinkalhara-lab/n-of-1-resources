// rare (C++) - a small CLI over the n-of-1-resources dataset.
//
// Part of the n-of-1-resources polyglot toolkit.
//
// Unlike the Python, Go and Rust tools, this one has no third-party
// dependencies, so it reads the flat TSV export rather than parsing JSON.
// Generate the export first:
//
//     python3 tools/python/rare.py export      # writes data/resources.tsv
//
// Build:  make -C tools/cpp
// Run:    ./tools/cpp/rare list
//         ./tools/cpp/rare search aso
//         ./tools/cpp/rare cat treatment
//         ./tools/cpp/rare stats
//         ./tools/cpp/rare validate
//
// Data path: defaults to data/resources.tsv, or set RARE_DATA to override.

#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <vector>

struct Resource {
  std::string id, name, category, region, url, audience, tags, description;
};

static const std::vector<std::string> VALID = {"community", "registry",
                                               "treatment", "reference"};

static bool isValidCategory(const std::string &c) {
  return std::find(VALID.begin(), VALID.end(), c) != VALID.end();
}

static std::string toLower(std::string s) {
  std::transform(s.begin(), s.end(), s.begin(),
                 [](unsigned char c) { return std::tolower(c); });
  return s;
}

static std::string dataPath() {
  const char *env = std::getenv("RARE_DATA");
  if (env && *env) return std::string(env);
  const std::vector<std::string> candidates = {
      "data/resources.tsv", "../../data/resources.tsv",
      "../../../data/resources.tsv"};
  for (const auto &c : candidates) {
    std::ifstream f(c);
    if (f.good()) return c;
  }
  return "data/resources.tsv";
}

static std::vector<std::string> splitTab(const std::string &line) {
  std::vector<std::string> out;
  std::string cur;
  for (char ch : line) {
    if (ch == '\t') {
      out.push_back(cur);
      cur.clear();
    } else {
      cur.push_back(ch);
    }
  }
  out.push_back(cur);
  return out;
}

static bool load(const std::string &path, std::vector<Resource> &rows) {
  std::ifstream in(path);
  if (!in) {
    std::cerr << "cannot read " << path << "\n";
    return false;
  }
  std::string line;
  bool first = true;
  while (std::getline(in, line)) {
    if (first) {
      first = false;  // skip header
      continue;
    }
    if (line.empty()) continue;
    auto c = splitTab(line);
    while (c.size() < 8) c.push_back("");
    Resource r;
    r.id = c[0];
    r.name = c[1];
    r.category = c[2];
    r.region = c[3];
    r.url = c[4];
    r.audience = c[5];
    r.tags = c[6];
    r.description = c[7];
    rows.push_back(r);
  }
  return true;
}

static bool matches(const Resource &r, const std::string &query) {
  std::string hay = toLower(r.name + " " + r.description + " " + r.category +
                            " " + r.region + " " + r.tags + " " + r.audience);
  return hay.find(toLower(query)) != std::string::npos;
}

static void printRows(const std::vector<const Resource *> &rows) {
  for (const auto *r : rows) {
    std::string cat = r->category;
    cat.resize(9, ' ');
    std::string name = r->name;
    name.resize(44, ' ');
    std::cout << "[" << cat << "] " << name << " " << r->url << "\n";
  }
  std::cout << "\n" << rows.size() << " resource(s)\n";
}

static void cmdStats(const std::vector<Resource> &rows) {
  std::map<std::string, int> cats, regions;
  for (const auto &r : rows) {
    cats[r.category]++;
    regions[r.region]++;
  }
  std::cout << "total: " << rows.size() << "\n\nby category:\n";
  for (const auto &c : VALID) {
    auto it = cats.find(c);
    if (it != cats.end()) {
      std::string k = c;
      k.resize(10, ' ');
      std::cout << "  " << k << " " << it->second << "\n";
    }
  }
  std::cout << "\nby region:\n";
  for (const auto &kv : regions) {
    std::string k = kv.first;
    k.resize(10, ' ');
    std::cout << "  " << k << " " << kv.second << "\n";
  }
}

static int cmdValidate(const std::vector<Resource> &rows) {
  std::vector<std::string> problems;
  std::set<std::string> seen;
  for (const auto &r : rows) {
    if (r.id.empty()) {
      problems.push_back("resource with empty id");
    } else if (seen.count(r.id)) {
      problems.push_back("duplicate id '" + r.id + "'");
    } else {
      seen.insert(r.id);
    }
    if (!isValidCategory(r.category))
      problems.push_back(r.id + ": invalid category '" + r.category + "'");
    if (r.url.rfind("http", 0) != 0)
      problems.push_back(r.id + ": url does not start with http");
    if (r.name.empty() || r.description.empty() || r.region.empty())
      problems.push_back(r.id + ": missing name/description/region");
  }
  if (!problems.empty()) {
    std::cout << "INVALID - " << problems.size() << " problem(s):\n";
    for (const auto &p : problems) std::cout << "  - " << p << "\n";
    return 1;
  }
  std::cout << "OK - " << rows.size()
            << " resources, all ids unique, categories/urls valid\n";
  return 0;
}

int main(int argc, char **argv) {
  if (argc < 2) {
    std::cerr << "usage: rare <list|search <q>|cat <category>|stats|validate>\n";
    return 2;
  }
  std::vector<Resource> rows;
  if (!load(dataPath(), rows)) return 1;

  std::string cmd = argv[1];

  if (cmd == "list") {
    std::vector<const Resource *> refs;
    for (const auto &r : rows) refs.push_back(&r);
    printRows(refs);
  } else if (cmd == "search") {
    if (argc < 3) {
      std::cerr << "search needs a query\n";
      return 2;
    }
    std::string q = argv[2];
    std::vector<const Resource *> refs;
    for (const auto &r : rows)
      if (matches(r, q)) refs.push_back(&r);
    printRows(refs);
  } else if (cmd == "cat") {
    if (argc < 3 || !isValidCategory(argv[2])) {
      std::cerr << "cat needs one of: community, registry, treatment, reference\n";
      return 2;
    }
    std::vector<const Resource *> refs;
    for (const auto &r : rows)
      if (r.category == argv[2]) refs.push_back(&r);
    printRows(refs);
  } else if (cmd == "stats") {
    cmdStats(rows);
  } else if (cmd == "validate") {
    return cmdValidate(rows);
  } else {
    std::cerr << "unknown command '" << cmd << "'\n";
    return 2;
  }
  return 0;
}
