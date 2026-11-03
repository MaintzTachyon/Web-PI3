# Guía de estructura y desarrollo web — Gemelo Digital del aula L419

## 1. Objetivo y alcance

El objetivo es construir una **única página web** que represente visualmente el aula L419 y muestre, sobre esa representación, los datos recibidos de los sensores.

La página debe abrir directamente mostrando el salón. **No debe incluir pestañas, secciones de navegación, páginas adicionales ni un panel independiente de estadísticas.** La representación del aula es la interfaz principal y los valores de los sensores deben aparecer junto a sus ubicaciones o al seleccionar sus marcadores.

En esta primera etapa se desarrollará únicamente la interfaz visual. Se utilizarán datos simulados para diseñar y probar la experiencia. La conexión con el sistema real se incorporará después, sin modificar el funcionamiento de adquisición de datos que ya existe en el repositorio:

<https://github.com/ARomuloChuquillanqui/estructurapi3>

### Alcance de esta etapa

- Crear la página única del aula L419.
- Dibujar el plano del salón en 2D mediante SVG.
- Representar mobiliario y elementos relevantes del aula.
- Ubicar visualmente los sensores en el plano.
- Mostrar valores, unidades, estado y última actualización de cada sensor.
- Permitir seleccionar un sensor para consultar sus datos en la misma página.
- Simular lecturas para probar la interfaz.
- Diseñar la estructura para que más adelante pueda consumir los datos reales.

### Fuera del alcance de esta etapa

- Modificar el firmware de los ESP32.
- Implementar la comunicación ESP-NOW entre los ESP32 y el ESP32 v4.
- Implementar la conexión Wi-Fi o MQTT.
- Configurar Mosquitto, Telegraf, InfluxDB o Grafana.
- Crear pestañas adicionales o una aplicación multipágina.
- Crear un backend de adquisición paralelo.

---

## 2. Arquitectura general del sistema

La interfaz web será una capa de visualización. No reemplazará ni duplicará el sistema de adquisición de datos.

La arquitectura existente del proyecto se debe conservar:

```text
Sensores
   │
   ▼
ESP32 de cada sensor
   │
   │ ESP-NOW
   ▼
ESP32 v4 (nodo central)
   │
   │ Wi-Fi / MQTT
   ▼
Mosquitto
   │
   ▼
Telegraf
   │
   ▼
InfluxDB
   │
   ├──────────────► Grafana
   │
   ▼
Interfaz web del aula L419
```

La interfaz web consultará los datos mediante una API o mecanismo de acceso controlado que se definirá durante la etapa de integración. El navegador no debe conectarse directamente a InfluxDB exponiendo tokens, contraseñas u otras credenciales.

**Importante:** antes de implementar la integración, se debe revisar el repositorio `estructurapi3` para identificar los nombres de los sensores, el formato de los mensajes y los campos que publica el ESP32 v4. La interfaz debe adaptarse a esos datos reales; no se deben inventar nombres de campos ni cambiar el protocolo de los dispositivos para ajustarlos al diseño web.

---

## 3. Tecnologías seleccionadas

| Tecnología | Función en el proyecto |
|---|---|
| HTML5 | Estructura del documento y elementos de la interfaz. |
| CSS3 | Diseño visual, distribución, colores y adaptación a diferentes pantallas. |
| JavaScript | Interactividad, selección de sensores y actualización de valores. |
| SVG | Plano 2D escalable e interactivo del aula. |
| Node.js | Entorno para ejecutar herramientas de desarrollo JavaScript. |
| npm | Gestor de paquetes para instalar y administrar dependencias. |
| Chart.js | Gráficos de historial, si se necesitan dentro de la vista del sensor. |
| Lucide | Iconos de interfaz. |

### ¿Node.js es una extensión de VS Code?

No. **Node.js no es una extensión de VS Code ni una biblioteca visual.** Es un entorno que permite ejecutar JavaScript fuera del navegador. En este proyecto se utilizará principalmente para ejecutar npm y administrar las dependencias y herramientas del frontend.

El navegador ejecutará el JavaScript de la página. Node.js no tiene que permanecer ejecutándose como servidor de producción para que una página estática funcione.

### Instalación en CachyOS / Arch Linux

```bash
sudo pacman -S nodejs npm
```

Verificar la instalación:

```bash
node --version
npm --version
```

---

## 4. Extensiones de Visual Studio Code

Las extensiones se instalan desde el panel de extensiones de VS Code (`Ctrl + Shift + X`) o mediante los comandos indicados.

### 4.1 Live Server

- **Identificador:** `ritwickdey.LiveServer`
- **Uso:** inicia un servidor local para abrir la página en el navegador y recargarla cuando se guardan cambios.
- **Cómo usarla:** abrir `index.html`, hacer clic derecho y elegir **Open with Live Server**. También se puede usar el botón **Go Live** de la barra inferior.
- **Importante:** Live Server es una herramienta de desarrollo; no es el servidor de producción ni conecta por sí mismo la página con los ESP32.

### 4.2 Prettier — Code formatter

- **Identificador:** `esbenp.prettier-vscode`
- **Uso:** mantiene un formato consistente en HTML, CSS, JavaScript y JSON.
- **Cómo usarla:** abrir la paleta de comandos (`Ctrl + Shift + P`), ejecutar **Format Document** y seleccionar Prettier si VS Code solicita un formateador.
- **Recomendación:** activar el formato al guardar en la configuración de VS Code.

### 4.3 ESLint

- **Identificador:** `dbaeumer.vscode-eslint`
- **Uso:** muestra problemas comunes y posibles errores en JavaScript.
- **Cómo usarla:** instalar la extensión y abrir los archivos `.js`; los avisos aparecen en el editor y en el panel **Problems**.
- **Nota:** la extensión utiliza la configuración y el paquete ESLint del proyecto. Se instalará y configurará cuando el código JavaScript tenga suficiente contenido para aplicar reglas.

### 4.4 SVG

- **Identificador:** `jock.svg`
- **Uso:** facilita la edición y visualización de archivos SVG.
- **Cómo usarla:** abrir `assets/aula-l419.svg` en VS Code para editar el marcado del plano. La vista previa depende de las funciones que proporcione la extensión; también se puede visualizar el SVG desde la página web.

### Instalación desde la terminal

```bash
code --install-extension ritwickdey.LiveServer
code --install-extension esbenp.prettier-vscode
code --install-extension dbaeumer.vscode-eslint
code --install-extension jock.svg
```

Estas son extensiones del editor. No deben confundirse con los paquetes instalados mediante npm.

---

## 5. Dependencias del proyecto

Para la primera versión se mantendrán las dependencias al mínimo.

### 5.1 Inicializar npm

Desde la carpeta raíz del proyecto:

```bash
npm init -y
```

Este comando crea `package.json`, archivo que registra los datos del proyecto y sus dependencias.

### 5.2 Instalar Chart.js

```bash
npm install chart.js
```

Chart.js se utilizará para mostrar, cuando corresponda, el historial de mediciones de un sensor dentro de la misma vista del aula. No se creará una pestaña exclusiva para gráficos.

### 5.3 Instalar Lucide

```bash
npm install lucide
```

Lucide proporciona iconos. Si se decide usar los iconos como SVG locales, se pueden incorporar directamente en el HTML/SVG sin depender de una carga externa.

### 5.4 ESLint (cuando se configure JavaScript)

```bash
npm install --save-dev eslint
```

ESLint es una dependencia de desarrollo. La extensión de VS Code permite ver sus avisos dentro del editor.

**No instalar todavía:** React, Vue, Angular, Flask, Express, clientes MQTT, clientes de InfluxDB ni paquetes para comunicación con ESP32. No son necesarios para diseñar la representación visual inicial.

---

## 6. Estructura de carpetas y archivos

Se propone la siguiente organización:

```text
gemelo-digital-l419/
│
├── index.html
├── package.json
├── package-lock.json
├── .gitignore
│
├── css/
│   ├── style.css
│   ├── layout.css
│   ├── components.css
│   └── plano.css
│
├── js/
│   ├── main.js
│   ├── plano.js
│   ├── sensores.js
│   ├── datos.js
│   └── graficos.js
│
├── assets/
│   ├── aula-l419.svg
│   ├── images/
│   └── icons/
│
└── data/
    └── sensores-demo.js
```

### Responsabilidad de cada archivo

| Archivo | Responsabilidad |
|---|---|
| `index.html` | Documento principal; contiene la vista única del aula. |
| `css/style.css` | Importa o reúne los estilos generales. |
| `css/layout.css` | Distribución de la página y adaptación a pantallas. |
| `css/components.css` | Tarjetas, etiquetas, botones, indicadores y ventanas de información. |
| `css/plano.css` | Estilos específicos del plano SVG y sus marcadores. |
| `js/main.js` | Inicialización de la interfaz y coordinación de módulos. |
| `js/plano.js` | Carga y comportamiento interactivo del plano. |
| `js/sensores.js` | Selección de sensores y actualización de sus indicadores. |
| `js/datos.js` | Obtención y distribución de datos; inicialmente utiliza datos simulados. |
| `js/graficos.js` | Creación y actualización de gráficos de historial. |
| `assets/aula-l419.svg` | Plano vectorial del aula. |
| `data/sensores-demo.js` | Lecturas ficticias para desarrollar y probar la interfaz. |

No es obligatorio mantener todos los archivos separados desde el primer día. La estructura permite crecer de forma ordenada sin introducir un framework.

---

## 7. Diseño de la única página web

Al abrir la web, el usuario debe ver directamente el aula L419. No debe tener que navegar a otra pestaña para encontrar el plano o los valores.

### 7.1 Distribución propuesta

```text
┌───────────────────────────────────────────────────────────────────┐
│ GEMELO DIGITAL — AULA L419                  Estado de conexión     │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  AULA L419                                      DATOS DEL AULA     │
│  ┌───────────────────────────────────────┐    ┌─────────────────┐  │
│  │                                       │    │ Temperatura     │  │
│  │          PLANO 2D DEL AULA            │    │     24.5 °C     │  │
│  │                                       │    ├─────────────────┤  │
│  │   [Sensor]                [Sensor]    │    │ Humedad         │  │
│  │                                       │    │      58 %       │  │
│  │        Mesas y mobiliario             │    ├─────────────────┤  │
│  │                                       │    │ CO₂             │  │
│  │   [Sensor]                [Sensor]    │    │     650 ppm     │  │
│  │                                       │    └─────────────────┘  │
│  └───────────────────────────────────────┘                         │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ Sensor seleccionado / detalle / historial de mediciones    │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Última actualización: 15:04:32                                  │
└───────────────────────────────────────────────────────────────────┘
```

Este esquema es conceptual. La distribución definitiva se ajustará al plano real y a la cantidad de sensores disponibles.

### 7.2 Encabezado

Debe incluir únicamente:

- Nombre del sistema: **Gemelo Digital — Aula L419**.
- Indicador general de conexión o disponibilidad de datos.
- Hora de la última actualización recibida.

No se incluirá una barra de navegación con pestañas.

### 7.3 Plano 2D

El plano será el elemento central de la interfaz.

Debe representar, según la información disponible:

- Límites y dimensiones del salón.
- Puerta y ventanas.
- Pizarra y proyector, si corresponde.
- Mesas, sillas y otros elementos relevantes.
- Ubicación física aproximada de cada sensor.

Se recomienda utilizar SVG porque permite escalar el plano sin perder calidad y asignar identificadores a cada sensor para interactuar con ellos desde JavaScript.

Cada marcador debe tener un identificador estable, por ejemplo `sensor-temperatura-01`. Al seleccionarlo, la página debe mostrar sus mediciones en el área de información, sin cambiar de página.

### 7.4 Información de sensores

Los indicadores visibles deben corresponder exclusivamente a los sensores realmente presentes en el proyecto. La lista final se confirmará revisando el repositorio y el inventario de hardware.

Cada indicador puede mostrar:

- Nombre o tipo del sensor.
- Valor medido.
- Unidad.
- Estado visual.
- Hora de la última lectura.

No se deben mostrar valores inventados como si fueran mediciones reales. Durante el desarrollo, todos los datos ficticios deben identificarse claramente como **DEMO** o **SIMULACIÓN**.

### 7.5 Detalle e historial

Al seleccionar un sensor:

- Se resalta su marcador en el plano.
- Se muestra su información en la misma página.
- Se puede presentar un gráfico de historial si existen datos de prueba.
- Se permite volver a la vista general del aula sin navegar a otra página.

---

## 8. Datos simulados durante el diseño

Antes de integrar el sistema real, se utilizarán datos ficticios con la misma estructura que se espera recibir en la futura integración. La estructura exacta se debe ajustar después de inspeccionar los mensajes del repositorio.

Ejemplo conceptual:

```javascript
const sensoresDemo = [
    {
        id: "sensor-temperatura-01",
        tipo: "temperatura",
        valor: 24.5,
        unidad: "°C",
        estado: "normal",
        actualizado: "15:04:32"
    },
    {
        id: "sensor-humedad-01",
        tipo: "humedad",
        valor: 58,
        unidad: "%",
        estado: "normal",
        actualizado: "15:04:32"
    }
];
```

Estos datos solo sirven para probar la presentación. No representan el formato definitivo de MQTT, ESP-NOW o InfluxDB.

---

## 9. Cómo crear el proyecto en CachyOS

El repositorio público `ARomuloChuquillanqui/estructurapi3` tiene en su raíz, según la vista del repositorio, las carpetas `gateway/`, `gateway_nube/`, `nodo_audio/`, `nodo_co2/`, `servidor_iot/` y `servidor_iot_prod/`, además del archivo `arquitectura_iot_gemelo_digital.png`. Por ello, el frontend debe añadirse como una carpeta independiente `web/` en la raíz, sin mover ni renombrar las carpetas existentes.

La vista pública del repositorio permite confirmar esos nombres, pero no fue posible inspeccionar el contenido interno de las carpetas desde esta consulta. Por tanto, esta guía no presupone nombres concretos de archivos, tópicos MQTT, campos JSON ni endpoints del firmware. Esos detalles se deben verificar localmente antes de conectar la interfaz.

### 9.1 Clonar el repositorio (si todavía no está clonado)

```bash
git clone https://github.com/ARomuloChuquillanqui/estructurapi3.git
cd estructurapi3
```

Si ya tienes el repositorio en tu equipo, entra a su carpeta y revisa su estructura antes de crear archivos.

### 9.2 Crear la carpeta del frontend

Desde la raíz del repositorio (donde actualmente aparecen `gateway/`, `gateway_nube/`, `nodo_audio/`, `nodo_co2/`, `servidor_iot/` y `servidor_iot_prod/`):

```bash
mkdir -p web
cd web

npm init -y

mkdir -p css js assets/images assets/icons data

touch index.html
touch css/style.css css/layout.css css/components.css css/plano.css
touch js/main.js js/plano.js js/sensores.js js/datos.js js/graficos.js
touch assets/aula-l419.svg
touch data/sensores-demo.js
```

### 9.3 Instalar las dependencias

```bash
npm install chart.js lucide
npm install --save-dev eslint
```

### 9.4 Abrir el frontend en VS Code

Desde la carpeta `web`:

```bash
code .
```

Para iniciar la vista previa, abre `index.html` con Live Server.

---

## 10. Integración futura con el repositorio

Cuando la interfaz visual esté terminada, se realizará una etapa independiente de integración.

Antes de conectar nada, revisar en `estructurapi3`:

1. Cómo se identifican los ESP32 secundarios.
2. Qué mensajes envían al ESP32 v4 mediante ESP-NOW.
3. Qué estructura de datos recibe el ESP32 v4.
4. Qué campos, nombres y unidades publica por MQTT.
5. Qué tópicos MQTT se utilizan.
6. Cómo se almacenan las mediciones en InfluxDB.

A partir de esa revisión se definirá cómo la web obtiene las mediciones. Si se consulta InfluxDB, las credenciales deben permanecer en el servidor o mecanismo seguro de acceso y nunca dentro de archivos JavaScript descargados por el navegador.

La futura integración debe respetar el flujo actual:

**ESP32 secundarios → ESP32 v4 → MQTT → Mosquitto → Telegraf → InfluxDB → interfaz web.**

Grafana puede seguir utilizándose para sus dashboards y exportaciones CSV. La página del gemelo digital tendrá como finalidad representar el aula y sus sensores, no reemplazar Grafana.

---

## 11. Orden recomendado de desarrollo

1. **Preparar el entorno:** instalar Node.js, npm y las extensiones de VS Code.
2. **Crear el frontend:** preparar carpetas, archivos y dependencias.
3. **Diseñar la página:** construir el encabezado y la distribución de la vista única.
4. **Dibujar el aula:** crear el SVG tomando como referencia un plano o fotografías reales.
5. **Ubicar los sensores:** colocar marcadores en sus posiciones físicas.
6. **Crear indicadores:** mostrar valores y estados con datos DEMO.
7. **Añadir interacción:** seleccionar marcadores y mostrar detalles sin cambiar de página.
8. **Añadir historial:** incorporar gráficos dentro de la misma vista cuando sean útiles.
9. **Validar la interfaz:** probar resolución, legibilidad, interacción y adaptación a pantallas.
10. **Integrar los datos reales:** revisar el repositorio y conectar la web con la fuente de datos existente.

## 12. Criterios para considerar terminado el frontend

- [ ] La página abre directamente en la representación del aula L419.
- [ ] No existen pestañas ni páginas adicionales.
- [ ] El plano representa la distribución real del salón.
- [ ] Los sensores aparecen en ubicaciones coherentes con el hardware.
- [ ] Cada sensor se puede seleccionar.
- [ ] Los valores y unidades se leen claramente.
- [ ] Los datos simulados están identificados como DEMO.
- [ ] La interfaz muestra cuándo se actualizó la información.
- [ ] La página funciona en la resolución de escritorio prevista.
- [ ] La estructura permite sustituir los datos simulados por datos reales sin rehacer el diseño.

---

## 13. Decisiones pendientes antes de dibujar el plano

Para que la representación sea fiel al aula y no una ilustración genérica, se necesita:

- Un plano arquitectónico del aula L419 o fotografías claras desde distintos ángulos.
- La distribución de mesas, sillas, puerta, ventanas, pizarra y proyector.
- La ubicación física de cada sensor.
- La lista definitiva de sensores y las variables que mide cada uno.

Con esta información se podrá construir el SVG del aula y diseñar los indicadores de acuerdo con el hardware real.
