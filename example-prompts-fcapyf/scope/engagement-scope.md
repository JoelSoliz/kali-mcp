# Acta de alcance — Pentest FCAPyF

> Fase PTES: Pre-compromiso · Documento de referencia para la ejecución y el Capítulo II.

---

## Identificación del engagement

| Campo | Valor |
|-------|-------|
| **Proyecto** | Monografía — Diplomado en Ciberseguridad UMSS 2026 |
| **Título** | Pruebas de penetración asistidas por agente de IA al portal web de la FCAPyF |
| **Evaluador** | Estudiante del diplomado (analista humano) + agente IA en Cursor |
| **Herramientas** | Servidor MCP `kali-mcp-remote` → Kali Linux |
| **Periodo** | Julio 2026 |

---

## Objetivo in-scope

| Activo | Detalle |
|--------|---------|
| **Host principal** | `fcapyf.umss.edu.bo` |
| **URL base** | https://fcapyf.umss.edu.bo/ |
| **Protocolos** | HTTPS (443), HTTP (80) si redirige |
| **Componentes** | Núcleo WordPress, tema, plugins públicos, REST API, XML-RPC, admin-ajax.php, assets estáticos |

---

## Objetivo out-of-scope

- Infraestructura de red de la UMSS
- Otros dominios y subdominios no servidos por el portal FCAPyF
- Panel `/wp-admin/` y funcionalidades que requieran autenticación
- Sistemas enlazados (Moodle, plataformas externas) salvo enlaces descubiertos en reconocimiento pasivo
- Pruebas de denegación de servicio
- Exfiltración o publicación de datos personales

---

## Modalidad de prueba

- **Tipo:** Pruebas de penetración de aplicación web
- **Perspectiva:** Caja negra (conocimiento nulo)
- **Credenciales:** Ninguna
- **Ubicación del evaluador:** Externo a la organización (Internet)

---

## Reglas de engagement

### Permitido

- Reconocimiento pasivo y activo moderado
- Escaneo de vulnerabilidades (WPScan, Nikto, ZAP, nmap en puertos web)
- Pruebas HTTP dirigidas (curl) sobre endpoints públicos
- Explotación controlada con PoC mínima
- Enumeración de usuarios vía REST (sin publicar en informe académico)
- Correlación con CVE/NVD/Wordfence
- **Prueba proporcional de autenticación** (ver sección *Política de autenticación*)

### Prohibido

- Ataques de denegación de servicio
- Fuerza bruta masiva o sin límite de intentos
- **Ataque por diccionario completo** (p. ej. rockyou, listas >50 contraseñas por usuario)
- **Hydra/medusa/wpscan --passwords** con wordlists extensas
- **XML-RPC `system.multicall`** con múltiples intentos de login en una sola petición (amplificación)
- Modificaciones persistentes sin reversión
- Acceso a sistemas fuera del alcance
- Divulgación pública de credenciales o PII

### Política de autenticación (enumeración → diccionario)

La enumeración de usuarios (REST, WPScan, author archives) **documenta exposición** bajo OWASP A07:2025. Un atacante real encadenaría esa lista con autenticación por diccionario vía login oculto (WPS Hide Login), `/wp-login.php` si se descubre, o XML-RPC.

**En este engagement académico:**

| Acción | ¿Permitida? | Propósito |
|--------|-------------|-----------|
| Enumerar usuarios (REST, WPScan `-u`) | Sí | Hallazgo A07; inventario anonimizado |
| Confirmar XML-RPC activo (`curl` GET/POST mínimo) | Sí | Hallazgo de configuración A02/A07 |
| **1–3 intentos fallidos** con contraseña obvia (`wrongpassword-test-2026`) por **un** usuario enumerado | Sí | Verificar si existe rate limiting / bloqueo / mensaje genérico |
| Documentar **viabilidad teórica** de diccionario sin ejecutarlo | Sí | Modelado de amenazas; remediación Cap. IV |
| Diccionario real, spray de contraseñas, hydra, multicall | **No** | Fuera de proporcionalidad; riesgo de lockout y DoS |

**Regla:** no buscar credenciales válidas. El objetivo es demostrar que la **superficie permite** el ataque encadenado, no comprometer cuentas. Si accidentalmente se obtuviera una credencial válida: **no reutilizar**, **no publicar**, detener pruebas de auth y reportar al analista.

**Clasificación esperada si XML-RPC/login responden sin límite:** debilidad de autenticación (A07) + configuración (A02), severidad media, impacto institucional elevado en recomendaciones — sin PoC de acceso exitoso.

### Proporcionalidad

- Limitar gobuster/dir brute a wordlists pequeñas y rate limiting razonable
- WPScan/Nikto: flags no destructivos
- nmap: preferir `-sV` en 80,443; evitar escaneos amplios de red

---

## Criterios de reversión (PoC)

Toda prueba de concepto que altere el estado del sistema debe:

1. Documentar estado previo (captura, response hash, timestamp)
2. Ejecutar cambio mínimo demostrativo
3. Capturar evidencia de impacto
4. **Revertir** al estado original inmediatamente
5. Registrar confirmación de reversión en `findings/F-NNN-*.json`

---

## Clasificación de hallazgos

- **OWASP Top 10:2025** para categoría
- **CVSS 3.1** para severidad técnica
- **Matriz de riesgo institucional** para priorización de remediación (Cap. IV)
- **Validación humana** obligatoria antes del inventario definitivo

---

## Entregables

| Entregable | Ubicación |
|------------|-----------|
| Artefactos JSON por fase | `pentesting-results/phases/` |
| Registros de hallazgos | `pentesting-results/findings/` |
| Informes de fase | `pentesting-results/reports/` |
| Narrativa académica | `monografia/capitulo-02-ejecucion-pruebas.md` |

---

## Autorización

Evaluación realizada en marco académico del **Diplomado en Ciberseguridad**, Facultad de Ciencias y Tecnología, UMSS, gestión 2026, conforme a principios de hacking ético [NIST SP 800-115] y consideraciones éticas del diseño metodológico de la monografía.

**Estado:** Pre-compromiso documentado — pendiente firma/confirmación institucional formal si el tribunal lo exige.
