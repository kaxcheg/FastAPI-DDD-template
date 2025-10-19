{{- define "fastapi-ddd-template.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "fastapi-ddd-template.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "fastapi-ddd-template.db-name" -}}
{{ include "fastapi-ddd-template.name" . }}-db
{{- end -}}

{{- define "fastapi-ddd-template.api-name" -}}
{{ include "fastapi-ddd-template.name" . }}-api
{{- end -}}

{{- define "fastapi-ddd-template.labels" -}}
app.kubernetes.io/name: {{ include "fastapi-ddd-template.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/part-of: {{ include "fastapi-ddd-template.name" . }}
app.kubernetes.io/version: {{ default .Chart.AppVersion .Values.api.version | quote }}
{{- end -}}

# component: api|db|db-bootstrap
{{- define "fastapi-ddd-template.selectorLabels" -}}
app.kubernetes.io/name: {{ include "fastapi-ddd-template.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: {{ .component | quote }}
{{- end -}}

# repo@sha256:digest или repo:tag
{{- define "fastapi-ddd-template.image" -}}
{{- $repo := .repository -}}
{{- $digest := .digest | default "" -}}
{{- $tag := .tag | default "latest" -}}
{{- if $digest -}}
{{ printf "%s@%s" $repo (printf "sha256:%s" (trimPrefix "sha256:" $digest)) }}
{{- else -}}
{{ printf "%s:%s" $repo $tag }}
{{- end -}}
{{- end -}}
