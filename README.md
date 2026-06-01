# Simulador de protocolo de coherencia de caché

Visualización de cómo van cambiando los estados en los bloques dentro de cada procesador utilizando una tabla de estados.

## Coherencia de caché en MP

Los multiprocesadores generalmente admiten almacenamiento en caché de datos tanto compartidos como privados.
* Los **datos privados** son utilizados por un solo procesador.
* Los **datos compartidos** son utilizados por múltiples procesadores, proporcionando esencialmente comunicación entre los procesadores a través de lecturas y escrituras de los datos compartidos.

Cuando se almacenan en caché datos compartidos, el valor puede ser replicado en múltiples cachés. Esto reduce la latencia de acceso y el ancho de banda requerido, pero introduce el **problema de la coherencia de caché**: diferentes procesadores pueden tener copias distintas del mismo dato.

Un sistema de memoria es **coherente** si:
* Una lectura de un procesador P a la posición X, que sigue de una escritura de P a X sin que ningún otro procesador haya escrito en X entre medias, siempre devuelve el valor escrito por P.
* Una lectura que sigue a una escritura de otro procesador devuelve el valor escrito, si ambos accesos están suficientemente separados y no hay otras escrituras intermedias.
* Las escrituras a la misma posición están **serializadas**: todos los procesadores ven las escrituras en el mismo orden.

---

## Esquemas de coherencia

Este simulador implementa coherencia basada en **sondeo (snooping)**:
* Todos los procesadores están conectados a un **bus compartido** y "escuchan" las transacciones.
* Antes de escribir en un bloque compartido se adquiere el bus para enviar invalidaciones o actualizaciones al resto de cachés.
* La serialización de accesos al bus garantiza el orden de las operaciones.

---

## Protocolo MSI

![Estados MSI](/images/estadosMSI.png)

---

El protocolo MSI es el protocolo de invalidación base, con **3 estados**.

* Los **estados** del protocolo son:
  * **Modificado (M)**: el bloque solo está en esta caché y ha sido modificado respecto a memoria principal.
  * **Compartido (S)**: el bloque puede estar en varias cachés y es idéntico al de memoria principal.
  * **Inválido (I)**: el bloque no es válido en esta caché.

---

* El **procesador** emite dos tipos de peticiones:
  * lecturas (**PrRd**)
  * escrituras (**PrWr**)

* Las lecturas o escrituras pueden ser a un bloque de memoria que existe en la caché (**hit**) o a uno que no existe (**miss**). En el último caso, el bloque que esté en la caché en la actualidad será reemplazado por el nuevo bloque, y si el bloque actual está en el estado modificado, su contenido será volcado a la memoria principal (**write-back**).

---

* El **bus** permite tres tipos de transacciones:
  * **_Lectura del bus_** (**BusRd**): El controlador de la caché pone la dirección en el bus y pide una copia que no piensa modificar. El sistema de memoria (posiblemente otra caché) proporciona el dato.

  * **_Lectura exclusiva del bus_** (**BusRdX**): El controlador de la caché pone la dirección en el bus y pide una copia exclusiva que piensa modificar. El sistema de memoria (posiblemente otra caché) proporciona el dato. Todas las demás cachés necesitan ser invalidadas.

  * **_Bus write-back_** (**BusWB**): El controlador de la caché pone la dirección y el contenido del bloque en el bus. La memoria principal se actualiza con el último contenido.

* **Limitación**: si un procesador quiere escribir sobre un bloque que ya tiene en estado **S**, debe emitir un `BusRdX` igualmente, generando tráfico innecesario. Esto se resuelve en MESI.

---

## Protocolo MESI

![Estados MESI](/images/estadosMESI.png)

---

Extensión del protocolo MSI que añade el estado **Exclusivo (E)** para evitar transacciones de bus innecesarias. También conocido como **protocolo Illinois** (Universidad de Illinois, 1984), con **4 estados**.

* Los **estados** del protocolo son:
  * **Modificado (M)**: el bloque solo está en esta caché y ha sido modificado respecto a memoria principal.
  * **Exclusivo (E)**: el bloque solo está en esta caché pero es idéntico al de memoria principal.
  * **Compartido (S)**: el bloque puede estar en varias cachés y es idéntico al de memoria principal.
  * **Inválido (I)**: el bloque no es válido en esta caché.

* La ventaja sobre MSI es que una escritura sobre un bloque en estado **E** puede pasar directamente a **M** sin generar ninguna transacción de bus, ya que se sabe que ningún otro procesador tiene copia del bloque.

* Para distinguir si hay otras copias al cargar un bloque, el bus señaliza:
  * **BusRd(S)**: hay otras cachés con el bloque → nuevo estado **S**.
  * **BusRd(Ŝ)**: ninguna otra caché tiene el bloque → nuevo estado **E**.

* **Variantes**:
  * **MESIF** — Intel Core i7. Añade el estado Forward.
  * **MOESI** — AMD64. Añade el estado Owned.

---

## Protocolo MESIF

![Estados MESIF](/images/estadosMESIF.png)

---

Variante del protocolo MESI utilizada en procesadores **Intel Core i7**. Añade el estado **Forward (F)** para optimizar quién responde a las peticiones de lectura entre cachés, con **5 estados**.

* Los **estados** del protocolo son:
  * **Modificado (M)**: el bloque solo está en esta caché y ha sido modificado respecto a memoria principal.
  * **Exclusivo (E)**: el bloque solo está en esta caché y es idéntico al de memoria principal.
  * **Compartido (S)**: el bloque puede estar en varias cachés y es idéntico al de memoria principal.
  * **Inválido (I)**: el bloque no es válido en esta caché.
  * **Forward (F)**: el bloque está compartido, pero esta caché es la designada para responder a las peticiones de lectura de otros procesadores, evitando que sea siempre la memoria principal quien sirva el dato.

* Entre todos los procesadores que comparten un bloque, solo uno puede estar en estado **F**; el resto permanecen en **S**. Cuando un nuevo procesador carga el bloque, el antiguo **F** pasa a **S** y el nuevo lector toma el estado **F**.

---

## Protocolo MOESI

![Estados MOESI](/images/estadosMOESI.jpg)

---

Variante del protocolo MESI utilizada en procesadores **AMD64**. Añade el estado **Owned (O)** para reducir las escrituras innecesarias a memoria principal, con **5 estados**.

* Los **estados** del protocolo son:
  * **Modificado (M)**: el bloque solo está en esta caché y ha sido modificado respecto a memoria principal.
  * **Owned (O)**: el bloque está modificado respecto a memoria principal, pero otras cachés pueden tener copias en estado **S**. El propietario es responsable de servir el dato a quien lo pida y de escribirlo en memoria cuando sea desalojado.
  * **Exclusivo (E)**: el bloque solo está en esta caché y es idéntico al de memoria principal.
  * **Compartido (S)**: el bloque puede estar en varias cachés. Puede no ser igual al de memoria principal si existe un propietario en estado **O**.
  * **Inválido (I)**: el bloque no es válido en esta caché.

* La ventaja sobre MESI es que cuando un procesador con un bloque en estado **M** recibe una petición de lectura de otro procesador, puede pasar a estado **O** y compartir el dato directamente **sin escribirlo primero en memoria principal**, reduciendo el tráfico hacia memoria.

---

## Uso del simulador

### Requisitos

* Python 3.8 o superior.
* Instalar dependencias:

```bash
pip install -r requirements.txt
```

### Ejecución

```bash
python main.py
```

### Interfaz gráfica

![Interfaz Grafica](/images/simulador.png)

La aplicación abre una ventana dividida en dos paneles:

**Panel izquierdo**
* **OPERACIÓN**: selector de procesador (`P1`–`P8`) y bloque de memoria (`A`–`H`), con los botones `LEER`, `ESCRIBIR` y `RESET`.
* **ESTADOS DE CACHÉ**: tabla que muestra el estado actual de cada bloque en cada procesador, actualizada tras cada operación.

![Panel Izquerdo](/images/panelIZQ.png)

**Panel derecho**
* **ÚLTIMO EVENTO DE BUS**: muestra la operación ejecutada, la transacción de bus generada, el origen del dato y el resultado de la operación.
* **LEYENDA**: indica los estados disponibles en el protocolo activo y su color correspondiente.
* **HISTORIAL**: registro de todas las operaciones realizadas en la sesión, en orden inverso.

![Panel Derecho](/images/panelDCH.png)

### Cambiar protocolo

En la cabecera de la aplicación hay un menú desplegable con los protocolos disponibles: `MSI`, `MESI`, `MESIF` y `MOESI`. Al cambiar de protocolo se resetea automáticamente la simulación.

![Cambio de protocolo](/images/arribaDCH.png)

### Configuración

El botón **Config** de la cabecera abre una ventana para ajustar:
* **Procesadores**: entre 2 y 8.
* **Bloques de memoria**: entre 2 y 8 (etiquetados como A, B, C…).

Cambiar la configuración resetea la simulación.

![Configuración](/images/configuracion.png)

### Leyenda de estados

| Color | Estado | Descripción |
|-------|--------|-------------|
| Gris `—` | No accedido | La posición no ha sido accedida aún |
| Gris `I` | Inválido | La copia en esta caché no es válida |
| Azul `S` | Compartido | Copia limpia, puede estar en varias cachés |
| Verde `E` | Exclusivo | Copia limpia, solo en esta caché *(MESI, MESIF, MOESI)* |
| Rojo `M` | Modificado | Copia sucia, solo en esta caché |
| Magenta `F` | Forward | Designada para responder a lecturas *(MESIF)* |
| Amarillo `O` | Owned | Copia sucia compartida, responsable de responder *(MOESI)* |

---

## Estructura del proyecto

```
├── main.py                 # Punto de entrada
├── requirements.txt        # Dependencias
└── src/
    ├── app.py              # Ventana principal y lógica de la interfaz gráfica
    ├── simulador.py        # Motor de simulación: estados y transiciones de bus
    ├── ventana_config.py   # Ventana modal de configuración
    └── constantes.py       # Colores e identificadores de bloques
```

* **`app.py`** — construye y gestiona toda la interfaz con `customtkinter`. Contiene la clase `App` que conecta las acciones del usuario (leer, escribir, reset, cambio de protocolo, configuración) con el simulador y actualiza la tabla, el panel de bus y el historial tras cada operación.

* **`simulador.py`** — contiene la clase `Simulador`, que implementa la lógica de coherencia para los cuatro protocolos. Gestiona el estado de cada bloque en cada caché, determina las transacciones de bus necesarias y registra el historial de operaciones.

* **`ventana_config.py`** — ventana modal (`CTkToplevel`) que permite ajustar el número de procesadores y bloques. Al guardar, llama al callback de `App` para reconfigurar el simulador y refrescar los menús.

* **`constantes.py`** — define los colores de fondo y texto para cada estado de caché, la lista de letras disponibles para los bloques y los colores generales de la interfaz.