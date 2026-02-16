#!/usr/bin/env bash
# Fetch obsolete HsapDv and MmusDv terms from Ubergraph and write TSV lookups.
# Usage: ./data/refresh_obsolete_stages.sh
# Output: data/obsolete_hsapdv.tsv  data/obsolete_mmusdv.tsv
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

fetch_obsolete() {
    local ont_owl="$1" out_file="$2"
    local query="PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?term ?label WHERE {
  ?term rdfs:isDefinedBy obo:${ont_owl} .
  ?term owl:deprecated \"true\"^^<http://www.w3.org/2001/XMLSchema#boolean> .
  OPTIONAL { ?term rdfs:label ?label }
}"

    local json
    json=$(curl -sf -G 'https://ubergraph.apps.renci.org/sparql' \
        --data-urlencode "query=${query}" \
        -H 'Accept: application/sparql-results+json' \
        --max-time 30)

    printf 'id\tlabel\n' > "$out_file"
    echo "$json" | python3 -c "
import json, sys, re
data = json.load(sys.stdin)
for b in data['results']['bindings']:
    iri = b['term']['value']
    # http://purl.obolibrary.org/obo/HsapDv_0000087 -> HsapDv:0000087
    curie = re.sub(r'.*/([A-Za-z]+)_(\d+)$', r'\1:\2', iri)
    label = b.get('label', {}).get('value', '')
    print(f'{curie}\t{label}')
" >> "$out_file"

    local count=$(($(wc -l < "$out_file") - 1))
    echo "  ${out_file##*/}: ${count} obsolete terms"
}

echo "Refreshing obsolete stage term lookups..."
fetch_obsolete "hsapdv.owl" "${SCRIPT_DIR}/obsolete_hsapdv.tsv"
fetch_obsolete "mmusdv.owl" "${SCRIPT_DIR}/obsolete_mmusdv.tsv"
echo "Done."
