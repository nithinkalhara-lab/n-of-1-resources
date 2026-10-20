// rare (Go) - a small CLI over data/resources.json.
//
// Part of the n-of-1-resources polyglot toolkit. Reads the same JSON dataset
// as the Python and Rust tools, and produces the same style of output.
//
// Build:  go build -o rare ./tools/go
// Run:    ./rare list
//         ./rare search aso
//         ./rare cat treatment
//         ./rare stats
//         ./rare validate
//
// Data path: defaults to data/resources.json (relative to the working
// directory), or set RARE_DATA to override.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"
)

type Resource struct {
	ID          string   `json:"id"`
	Name        string   `json:"name"`
	Category    string   `json:"category"`
	Region      string   `json:"region"`
	URL         string   `json:"url"`
	Audience    []string `json:"audience"`
	Tags        []string `json:"tags"`
	Description string   `json:"description"`
}

type Dataset struct {
	Version   string     `json:"version"`
	Resources []Resource `json:"resources"`
}

var validCategories = []string{"community", "registry", "treatment", "reference"}

func isValidCategory(c string) bool {
	for _, v := range validCategories {
		if v == c {
			return true
		}
	}
	return false
}

func dataPath() string {
	if p := os.Getenv("RARE_DATA"); p != "" {
		return p
	}
	candidates := []string{
		"data/resources.json",
		"../../data/resources.json",
		"../../../data/resources.json",
	}
	for _, c := range candidates {
		if _, err := os.Stat(c); err == nil {
			return c
		}
	}
	return candidates[0]
}

func load(path string) ([]Resource, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("cannot read %s: %w", path, err)
	}
	var ds Dataset
	if err := json.Unmarshal(raw, &ds); err != nil {
		return nil, fmt.Errorf("invalid JSON in %s: %w", path, err)
	}
	return ds.Resources, nil
}

func matches(r Resource, query string) bool {
	hay := strings.ToLower(strings.Join([]string{
		r.Name, r.Description, r.Category, r.Region,
		strings.Join(r.Tags, " "), strings.Join(r.Audience, " "),
	}, " "))
	return strings.Contains(hay, strings.ToLower(query))
}

func printRows(rows []Resource) {
	for _, r := range rows {
		fmt.Printf("[%-9s] %-44s %s\n", r.Category, r.Name, r.URL)
	}
	fmt.Printf("\n%d resource(s)\n", len(rows))
}

func cmdStats(rows []Resource) {
	cats := map[string]int{}
	regions := map[string]int{}
	for _, r := range rows {
		cats[r.Category]++
		regions[r.Region]++
	}
	fmt.Printf("total: %d\n\nby category:\n", len(rows))
	for _, c := range validCategories {
		if n, ok := cats[c]; ok {
			fmt.Printf("  %-10s %d\n", c, n)
		}
	}
	fmt.Println("\nby region:")
	keys := make([]string, 0, len(regions))
	for k := range regions {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		fmt.Printf("  %-10s %d\n", k, regions[k])
	}
}

func cmdValidate(rows []Resource) int {
	problems := []string{}
	seen := map[string]bool{}
	for _, r := range rows {
		if r.ID == "" {
			problems = append(problems, "resource with empty id")
		} else if seen[r.ID] {
			problems = append(problems, "duplicate id '"+r.ID+"'")
		} else {
			seen[r.ID] = true
		}
		if !isValidCategory(r.Category) {
			problems = append(problems, r.ID+": invalid category '"+r.Category+"'")
		}
		if !strings.HasPrefix(r.URL, "http") {
			problems = append(problems, r.ID+": url does not start with http")
		}
		if r.Name == "" || r.Description == "" || r.Region == "" {
			problems = append(problems, r.ID+": missing name/description/region")
		}
	}
	if len(problems) > 0 {
		fmt.Printf("INVALID - %d problem(s):\n", len(problems))
		for _, p := range problems {
			fmt.Println("  -", p)
		}
		return 1
	}
	fmt.Printf("OK - %d resources, all ids unique, categories/urls valid\n", len(rows))
	return 0
}

func main() {
	args := os.Args[1:]
	if len(args) == 0 {
		fmt.Println("usage: rare <list|search <q>|cat <category>|stats|validate>")
		os.Exit(2)
	}

	rows, err := load(dataPath())
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	switch args[0] {
	case "list":
		printRows(rows)
	case "search":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "search needs a query")
			os.Exit(2)
		}
		q := strings.Join(args[1:], " ")
		out := []Resource{}
		for _, r := range rows {
			if matches(r, q) {
				out = append(out, r)
			}
		}
		printRows(out)
	case "cat":
		if len(args) < 2 || !isValidCategory(args[1]) {
			fmt.Fprintln(os.Stderr, "cat needs one of: community, registry, treatment, reference")
			os.Exit(2)
		}
		out := []Resource{}
		for _, r := range rows {
			if r.Category == args[1] {
				out = append(out, r)
			}
		}
		printRows(out)
	case "stats":
		cmdStats(rows)
	case "validate":
		os.Exit(cmdValidate(rows))
	default:
		fmt.Fprintln(os.Stderr, "unknown command '"+args[0]+"'")
		os.Exit(2)
	}
}
