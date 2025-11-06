{{- define "dddapitpl.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "dddapitpl.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "dddapitpl.db-name" -}}
{{- if .Values.config.data.DB_HOST -}}
{{- .Values.config.data.DB_HOST -}}
{{- else -}}
{{- printf "%s-db" (include "dddapitpl.name" .) -}}
{{- end -}}
{{- end -}}

{{- define "dddapitpl.db-meta-name" -}}
{{- printf "%s-db" (include "dddapitpl.name" .) -}}
{{- end -}}


{{- define "dddapitpl.api-name" -}}
{{ include "dddapitpl.name" . }}-api
{{- end -}}

{{- define "dddapitpl.labels" -}}
app.kubernetes.io/name: {{ include "dddapitpl.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/part-of: {{ include "dddapitpl.name" . }}
app.kubernetes.io/version: {{ default .Chart.AppVersion .Values.api.version | quote }}
{{- end -}}

# component: api|db|db-bootstrap
{{- define "dddapitpl.selectorLabels" -}}
app.kubernetes.io/name: {{ include "dddapitpl.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: {{ .component | quote }}
{{- end -}}

# repo@sha256:digest или repo:tag
{{- define "dddapitpl.image" -}}
{{- $repo := .repository -}}
{{- $digest := .digest | default "" -}}
{{- $tag := .tag | default "latest" -}}
{{- if $digest -}}
{{ printf "%s@%s" $repo (printf "sha256:%s" (trimPrefix "sha256:" $digest)) }}
{{- else -}}
{{ printf "%s:%s" $repo $tag }}
{{- end -}}
{{- end -}}
