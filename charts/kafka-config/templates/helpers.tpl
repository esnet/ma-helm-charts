{{/*
Expand the name of the chart.
*/}}
{{- define "kafka.name" -}}
{{- .Values.config.kafka.clusterName | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels (applied to all resources).
*/}}
{{- define "kafka.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "kafka.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Component-scoped labels. Call with (list . "component-name").
Extends kafka.labels with app.kubernetes.io/component.
*/}}
{{- define "kafka.componentLabels" -}}
{{- $ctx := index . 0 -}}
{{- $component := index . 1 -}}
{{ include "kafka.labels" $ctx }}
app.kubernetes.io/component: {{ $component }}
{{- end }}
