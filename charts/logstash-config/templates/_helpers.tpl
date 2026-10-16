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
Validate a transform index.
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
Build the full sorted list of pipeline config sources: kafka input (index 1, when enabled),
user-defined transforms, and elasticsearch output (index 999, when enabled). Uses insertion
sort on .index. Emits a YAML array of {index, configMap} — parse with fromYamlArray.
Call with (list . transforms): {{ include "logstash.pipelineSources" (list . .Values.pipeline.transforms) }}
*/}}
{{- define "logstash.pipelineSources" -}}
{{- $ctx := index . 0 -}}
{{- $transforms := index . 1 -}}
{{- $release := $ctx.Release.Name -}}
{{- $combined := list -}}
{{- if $ctx.Values.kafka.enabled -}}
  {{- $combined = append $combined (dict "index" 1 "configMap" (printf "%s-kafka-input" $release)) -}}
{{- end -}}
{{- range $transforms }}
{{- $combined = append $combined (dict "index" (int .index) "configMap" .configMap) }}
{{- end }}
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
Render podTemplate volumes — one configMap volume per pipeline source,
named by its zero-padded index (e.g. "pipeline-020").
Call with (list . transforms): {{ include "logstash.pipelineVolumes" (list . .Values.pipeline.transforms) }}
*/}}
{{- define "logstash.pipelineVolumes" -}}
{{- $sources := include "logstash.pipelineSources" . | fromYamlArray -}}
{{- range $sources }}
- name: pipeline-{{ include "logstash.pad3" .index }}
  configMap:
    name: {{ .configMap }}
{{- end }}
{{- end -}}

{{/*
Render container volumeMounts for the pipeline sources — each mounted into
its own subdirectory under /usr/share/logstash/pipeline/custom so Logstash's
recursive glob (see path.config on the Logstash resource) picks them all up,
without using subPath (which would break ConfigMap live-reload).
Call with (list . transforms): {{ include "logstash.pipelineVolumeMounts" (list . .Values.pipeline.transforms) }}
*/}}
{{- define "logstash.pipelineVolumeMounts" -}}
{{- $sources := include "logstash.pipelineSources" . | fromYamlArray -}}
{{- range $sources }}
- name: pipeline-{{ include "logstash.pad3" .index }}
  mountPath: /usr/share/logstash/pipeline/custom/{{ include "logstash.pad3" .index }}
  readOnly: true
{{- end }}
{{- end -}}
