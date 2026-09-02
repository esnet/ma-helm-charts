{{/*
Common labels applied to all chart-managed resources.
*/}}
{{- define "clickhouse.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Values.config.clickhouse_version | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
