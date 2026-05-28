{{/*
Common labels
*/}}
{{- define "pdf-merger.labels" -}}
app.kubernetes.io/name: {{ .Release.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "pdf-merger.selectorLabels" -}}
app: {{ .Release.Name }}
{{- end -}}

{{- define "pdf-merger.fullname" -}}
{{ .Release.Name }}
{{- end -}}
