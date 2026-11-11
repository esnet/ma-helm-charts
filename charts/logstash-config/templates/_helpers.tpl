{{/*
Release name, truncated to 63 chars.
*/}}
{{- define "logstash.name" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to all resources.
*/}}
{{- define "logstash.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "logstash.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Zero-pad an integer to 3 digits.
Call with a plain integer value: {{ include "logstash.pad3" 20 }} → "020"
Hard-fails if the value exceeds 999.
*/}}
{{- define "logstash.pad3" -}}
{{- $n := int . -}}
{{- if gt $n 999 -}}
  {{- fail (printf "pipeline index %d exceeds 3-digit maximum (999)" $n) -}}
{{- else if lt $n 0 -}}
  {{- fail (printf "pipeline index %d must be a positive integer" $n) -}}
{{- else if lt $n 10 -}}
  {{- printf "00%d" $n -}}
{{- else if lt $n 100 -}}
  {{- printf "0%d" $n -}}
{{- else -}}
  {{- printf "%d" $n -}}
{{- end -}}
{{- end }}

{{/*
Merge pipeline.transforms (legacy) and pipeline.sources into a single
normalised list. Each entry has: index (int), type (configMap|inline|fromImage),
and one of: configMap (string), inline (string), fromImage (string).

Entries from pipeline.transforms are treated as type=configMap for backward compat.
Entries from pipeline.sources with no explicit type field are inferred from which
key is present (configMap/inline/fromImage).
*/}}
{{- define "logstash.allSources" -}}
{{- $ctx := index . 0 -}}
{{- $out := list -}}
{{- range $ctx.Values.pipeline.transforms -}}
  {{- $out = append $out (dict "index" (int .index) "type" "configMap" "configMap" .configMap) -}}
{{- end -}}
{{- range $ctx.Values.pipeline.sources -}}
  {{- $type := "" -}}
  {{- if .type -}}
    {{- $type = .type -}}
  {{- else if .configMap -}}
    {{- $type = "configMap" -}}
  {{- else if .inline -}}
    {{- $type = "inline" -}}
  {{- else if .fromImage -}}
    {{- $type = "fromImage" -}}
  {{- else -}}
    {{- fail (printf "pipeline.sources entry at index %d has no recognisable type (configMap/inline/fromImage)" (int .index)) -}}
  {{- end -}}
  {{- $entry := dict "index" (int .index) "type" $type -}}
  {{- if eq $type "configMap" -}}
    {{- $entry = merge $entry (dict "configMap" .configMap) -}}
  {{- else if eq $type "inline" -}}
    {{- $entry = merge $entry (dict "inline" .inline) -}}
  {{- else if eq $type "fromImage" -}}
    {{- $entry = merge $entry (dict "fromImage" .fromImage) -}}
  {{- end -}}
  {{- $out = append $out $entry -}}
{{- end -}}
{{- toYaml $out -}}
{{- end -}}

{{/*
Validate a transform/source index.
001 is reserved when kafka.enabled is true; 999 is reserved when elasticsearch.enabled is true.
Call with (list . $index).
*/}}
{{- define "logstash.validateTransformIndex" -}}
{{- $ctx := index . 0 -}}
{{- $n := int (index . 1) -}}
{{- if le $n 0 -}}
  {{- fail (printf "transform index %d must be a positive integer" $n) -}}
{{- else if and (le $n 1) $ctx.Values.kafka.enabled -}}
  {{- fail (printf "transform index %d is reserved (001 = kafka input); set kafka.enabled=false to use this slot" $n) -}}
{{- else if gt $n 999 -}}
  {{- fail (printf "transform index %d exceeds maximum (999)" $n) -}}
{{- else if and (ge $n 999) $ctx.Values.elasticsearch.enabled -}}
  {{- fail (printf "transform index %d is reserved (999 = elasticsearch output); set elasticsearch.enabled=false to use this slot" $n) -}}
{{- end -}}
{{- end }}

{{/*
Build the full sorted list of pipeline config sources for volumes/mounts:
kafka input (index 1, when enabled), configMap and inline sources (by index),
and elasticsearch output (index 999, when enabled).
fromImage sources are excluded — they use a shared emptyDir, not per-source volumes.
Emits a YAML array of {index, configMap} — parse with fromYamlArray.
Call with (list . transforms): {{ include "logstash.pipelineSources" (list . .Values.pipeline.transforms) }}
*/}}
{{- define "logstash.pipelineSources" -}}
{{- $ctx := index . 0 -}}
{{- $release := $ctx.Release.Name -}}
{{- $combined := list -}}
{{- if $ctx.Values.kafka.enabled -}}
  {{- $combined = append $combined (dict "index" 1 "configMap" (printf "%s-kafka-input" $release)) -}}
{{- end -}}
{{- $allSources := include "logstash.allSources" (list $ctx) | fromYamlArray -}}
{{- range $allSources -}}
  {{- if or (eq .type "configMap") (eq .type "inline") -}}
    {{- $cmName := "" -}}
    {{- if eq .type "configMap" -}}
      {{- $cmName = .configMap -}}
    {{- else -}}
      {{- $cmName = printf "%s-inline-%s" $release (include "logstash.pad3" .index) -}}
    {{- end -}}
    {{- $combined = append $combined (dict "index" (int .index) "configMap" $cmName) -}}
  {{- end -}}
{{- end -}}
{{- if $ctx.Values.elasticsearch.enabled -}}
  {{- $combined = append $combined (dict "index" 999 "configMap" (printf "%s-elasticsearch-output" $release)) -}}
{{- end -}}
{{- $sorted := list -}}
{{- range $a := $combined -}}
  {{- $inserted := false -}}
  {{- $newSorted := list -}}
  {{- range $b := $sorted -}}
    {{- if and (not $inserted) (lt (int $a.index) (int $b.index)) -}}
      {{- $newSorted = append $newSorted $a -}}
      {{- $inserted = true -}}
    {{- end -}}
    {{- $newSorted = append $newSorted $b -}}
  {{- end -}}
  {{- if not $inserted -}}
    {{- $newSorted = append $newSorted $a -}}
  {{- end -}}
  {{- $sorted = $newSorted -}}
{{- end -}}
{{- toYaml $sorted -}}
{{- end -}}

{{/*
Return true if any pipeline.sources entry has type fromImage.
*/}}
{{- define "logstash.hasImageSources" -}}
{{- $ctx := index . 0 -}}
{{- $allSources := include "logstash.allSources" (list $ctx) | fromYamlArray -}}
{{- $found := false -}}
{{- range $allSources -}}
  {{- if eq .type "fromImage" -}}
    {{- $found = true -}}
  {{- end -}}
{{- end -}}
{{- $found -}}
{{- end -}}

{{/*
Render podTemplate volumes — one configMap volume per pipeline source,
named by its zero-padded index (e.g. "pipeline-020").
Plus pipeline-app emptyDir when fromImage sources exist.
Call with (list . transforms): {{ include "logstash.pipelineVolumes" (list . .Values.pipeline.transforms) }}
*/}}
{{- define "logstash.pipelineVolumes" -}}
{{- $sources := include "logstash.pipelineSources" . | fromYamlArray -}}
{{- range $sources }}
- name: pipeline-{{ include "logstash.pad3" .index }}
  configMap:
    name: {{ .configMap }}
{{- end }}
{{- $ctx := index . 0 -}}
{{- if eq (include "logstash.hasImageSources" (list $ctx)) "true" }}
- name: pipeline-app
  emptyDir: {}
{{- end }}
{{- end -}}

{{/*
Render container volumeMounts for the pipeline sources.
ConfigMap/inline sources each mount into their own subdirectory under custom/.
fromImage sources share the pipeline-app emptyDir at custom/app/.
*/}}
{{- define "logstash.pipelineVolumeMounts" -}}
{{- $sources := include "logstash.pipelineSources" . | fromYamlArray -}}
{{- range $sources }}
- name: pipeline-{{ include "logstash.pad3" .index }}
  mountPath: /usr/share/logstash/pipeline/custom/{{ include "logstash.pad3" .index }}
  readOnly: true
{{- end }}
{{- $ctx := index . 0 -}}
{{- if eq (include "logstash.hasImageSources" (list $ctx)) "true" }}
- name: pipeline-app
  mountPath: /usr/share/logstash/pipeline/custom/app
{{- end }}
{{- end -}}
