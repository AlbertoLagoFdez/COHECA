# Simulador de protocolo de coherencia de caché

Visualización de cómo van cambiando los estados en los bloques dentro de cada procesador utilizando una tabla de estados.
---
## Coherencia de caché en MP
Los multiprocesadores generalmente admiten almacenamiento en caché de datos tanto compartidos como privados.
* Los datos privados son utilizados por un solo procesador.
* Mientras que los datos compartidos son utilizados por múltiples procesadores, proporcionando esencialmente comunicacion entre los procesadors a través de lecturas y escrituras de los datos compartidos.
---
## Protocolo MSI
![Estados MSI](/images/estadosMSI.png)
---
* El **procesador** emite dos tipos de peticiones:
  * lecturas (**PrRd**)
  * escrituras (**PrWr**)

* Las lecturas o escrituras pueden ser un bloque de memoria que existe en la caché (**hit**) o a uno que no existe (**miss**). En el último caso, el bloque que esté en la caché en la actualidad será reemplazado por el nuevo bloque, y si el bloque actual está en el estado modificado, su contenido será volcado a la memoria principal (**write-back**).
---
* El **bus** permite tres tipos de transacciones:
  * **_Lectura del bus_** (**BusRd**): El controlados de la caché pone la dirección en el bus y pide una copia que no piensa modificar. El sistema de memoria (posiblemente otra caché) proporciona el dato.

  * **_Lectura exclusiva del bus_** (**BusRdX**): El controlador de la caché pone la dirección en el bus y pide una copia exclusiva que piensa modificar. El sistema de memoria (posiblemente otra caché) proporcional el dato. Todas las demás cachés necesitan ser invalidadas.
  
  * **_Bus write-back_** (**BusWB**): el controlador de la caché pone la dirección y el contenido para el bloque de la memoria en el bus. La memoria principas se actualiza con el ultimo contenido.

