{{- define "fastapi-ddd-template-api.name" -}}
{{- if .Values.nameOverride }}{{ .Values.nameOverride }}{{ else }}{{ include "fastapi-ddd-template-api.fullname" . }}{{ end -}}
{{- end }}

{{- define "fastapi-ddd-template-api.fullname" -}}
{{- if .Values.fullnameOverride }}
{{ .Values.fullnameOverride }}
{{- else -}}
{{- printf "%s" .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end }}

{{/*
Полное имя image со сборкой по digest если задан.
*/}}
{{- define "fastapi-ddd-template-api.image" -}}
{{- $repo := .Values.image.repository -}}
{{- $tag := .Values.image.tag | default "" -}}
{{- $digest := .Values.image.digest | default "" -}}
{{- if $digest -}}
{{ printf "%s@sha256:%s" $repo $digest }}
{{- else if $tag -}}
{{ printf "%s:%s" $repo $tag }}
{{- else -}}
{{ $repo }}
{{- end -}}
{{- end }}


{{- define "fastapi-ddd-template-api.configName" -}}
{{- if and .Values.config.enabled (not .Values.config.existingName) -}}
{{ include "fastapi-ddd-template-api.fullname" . }}-config
{{- else -}}
{{- default "" .Values.config.existingName -}}
{{- end -}}
{{- end }}
