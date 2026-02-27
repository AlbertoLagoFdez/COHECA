from enum import Enum

# ─────────────────────────────────────────────
#  Estados
# ─────────────────────────────────────────────

class EstadoMSI(Enum):
    I = "I"; S = "S"; M = "M"

class EstadoMESI(Enum):
    I = "I"; S = "S"; E = "E"; M = "M"

class EstadoMESIF(Enum):
    I = "I"; S = "S"; E = "E"; M = "M"; F = "F"

class EstadoMOESI(Enum):
    I = "I"; S = "S"; E = "E"; M = "M"; O = "O"

# ─────────────────────────────────────────────
#  Simulador
# ─────────────────────────────────────────────

class Simulador:
    def __init__(self, protocolo="MSI", num_procesadores=3, posiciones=None):
        self.protocolo = protocolo.upper()
        self.num_procesadores = num_procesadores
        self.posiciones = posiciones or ["A", "B", "C", "D"]
        self._set_enum()
        self._reset_estado()

    def _set_enum(self):
        mapa = {"MSI": EstadoMSI, "MESI": EstadoMESI, "MESIF": EstadoMESIF, "MOESI": EstadoMOESI}
        self.EstadoEnum = mapa[self.protocolo]

    def _reset_estado(self):
        self.cache = {p: {pos: self.EstadoEnum.I for pos in self.posiciones} for p in range(self.num_procesadores)}
        self.tocado = {p: {pos: False for pos in self.posiciones} for p in range(self.num_procesadores)}
        self.memoria_valida = {pos: True for pos in self.posiciones}
        self.historial = []

    def cambiar_protocolo(self, protocolo):
        self.protocolo = protocolo.upper()
        self._set_enum()
        self._reset_estado()

    def reconfigurar(self, num_procesadores, posiciones):
        self.num_procesadores = num_procesadores
        self.posiciones = posiciones
        self._reset_estado()

    def resetear(self):
        self._reset_estado()

    # ── Helpers internos ──────────────────────────

    def _hay_copia_valida(self, pos, excepto=None):
        for p in range(self.num_procesadores):
            if p == excepto: continue
            if self.cache[p][pos] != self.EstadoEnum.I: return True
        return False

    def _hay_modificado(self, pos, excepto=None):
        for p in range(self.num_procesadores):
            if p == excepto: continue
            if self.cache[p][pos] == self.EstadoEnum.M: return p
        return None

    def _hay_owned(self, pos, excepto=None):
        for p in range(self.num_procesadores):
            if p == excepto: continue
            if hasattr(self.EstadoEnum, 'O') and self.cache[p][pos] == self.EstadoEnum.O: return p
        return None

    def _hay_forward(self, pos, excepto=None):
        for p in range(self.num_procesadores):
            if p == excepto: continue
            if hasattr(self.EstadoEnum, 'F') and self.cache[p][pos] == self.EstadoEnum.F: return p
        return None

    def _invalidar_otros(self, pos, excepto):
        for p in range(self.num_procesadores):
            if p != excepto:
                if self.cache[p][pos] != self.EstadoEnum.I:
                    self.tocado[p][pos] = True
                self.cache[p][pos] = self.EstadoEnum.I

    # ── Operaciones ───────────────────────────────

    def leer(self, proc, pos):
        estado_actual = self.cache[proc][pos]
        eventos_bus = []
        origen_dato = "Memoria"

        if estado_actual != self.EstadoEnum.I:
            resultado = f"ACIERTO de lectura en P{proc+1}[{pos}] — estado: {estado_actual.value}"
            return self._registrar(proc, "READ", pos, resultado, [], estado_actual, origen_dato, acierto=True)

        eventos_bus.append("BusRd")

        if self.protocolo == "MSI":
            duenio_M = self._hay_modificado(pos, excepto=proc)
            if duenio_M is not None:
                eventos_bus.append("Flush")
                origen_dato = f"Caché P{duenio_M+1}"
                self.cache[duenio_M][pos] = self.EstadoEnum.S
                self.tocado[duenio_M][pos] = True
                self.memoria_valida[pos] = True
            nuevo_estado = self.EstadoEnum.S

        elif self.protocolo == "MESI":
            duenio_M = self._hay_modificado(pos, excepto=proc)
            if duenio_M is not None:
                eventos_bus.append("Flush")
                origen_dato = f"Caché P{duenio_M+1}"
                self.cache[duenio_M][pos] = self.EstadoEnum.S
                self.tocado[duenio_M][pos] = True
                self.memoria_valida[pos] = True
            hay_otra = self._hay_copia_valida(pos, excepto=proc)
            if hay_otra:
                eventos_bus[0] = "BusRd(S)"; nuevo_estado = self.EstadoEnum.S
            else:
                eventos_bus[0] = "BusRd(Ŝ)"; nuevo_estado = self.EstadoEnum.E

        elif self.protocolo == "MESIF":
            duenio_M = self._hay_modificado(pos, excepto=proc)
            if duenio_M is not None:
                eventos_bus.append("Flush")
                origen_dato = f"Caché P{duenio_M+1}"
                self.cache[duenio_M][pos] = self.EstadoEnum.S
                self.tocado[duenio_M][pos] = True
                self.memoria_valida[pos] = True
            hay_otra = self._hay_copia_valida(pos, excepto=proc)
            if hay_otra:
                eventos_bus[0] = "BusRd(S)"
                forward_actual = self._hay_forward(pos, excepto=proc)
                if forward_actual is not None:
                    origen_dato = f"Caché P{forward_actual+1} (Forward)"
                    self.cache[forward_actual][pos] = self.EstadoEnum.S
                    self.tocado[forward_actual][pos] = True
                else:
                    origen_dato = "Caché (compartida)"
                nuevo_estado = self.EstadoEnum.F
            else:
                eventos_bus[0] = "BusRd(Ŝ)"; nuevo_estado = self.EstadoEnum.E

        elif self.protocolo == "MOESI":
            duenio_M = self._hay_modificado(pos, excepto=proc)
            duenio_O = self._hay_owned(pos, excepto=proc)
            if duenio_M is not None:
                origen_dato = f"Caché P{duenio_M+1} (Owned)"
                self.cache[duenio_M][pos] = self.EstadoEnum.O
                self.tocado[duenio_M][pos] = True
                nuevo_estado = self.EstadoEnum.S
            elif duenio_O is not None:
                origen_dato = f"Caché P{duenio_O+1} (Owned)"
                nuevo_estado = self.EstadoEnum.S
            else:
                hay_otra = self._hay_copia_valida(pos, excepto=proc)
                nuevo_estado = self.EstadoEnum.S if hay_otra else self.EstadoEnum.E

        self.cache[proc][pos] = nuevo_estado
        self.tocado[proc][pos] = True
        resultado = f"Fallo de lectura P{proc+1}[{pos}]: I → {nuevo_estado.value}"
        return self._registrar(proc, "READ", pos, resultado, eventos_bus, nuevo_estado, origen_dato, acierto=False)

    def escribir(self, proc, pos):
        estado_actual = self.cache[proc][pos]
        eventos_bus = []
        origen_dato = "—"

        if estado_actual == self.EstadoEnum.M:
            resultado = f"ACIERTO de escritura en P{proc+1}[{pos}] — estado: M"
            return self._registrar(proc, "WRITE", pos, resultado, [], estado_actual, origen_dato, acierto=True)

        if hasattr(self.EstadoEnum, 'E') and estado_actual == self.EstadoEnum.E:
            resultado = f"Escritura silenciosa P{proc+1}[{pos}]: E → M (sin bus)"
            self.cache[proc][pos] = self.EstadoEnum.M
            self.tocado[proc][pos] = True
            return self._registrar(proc, "WRITE", pos, resultado, [], self.EstadoEnum.M, "—", acierto=True)

        if hasattr(self.EstadoEnum, 'F') and estado_actual == self.EstadoEnum.F:
            eventos_bus.append("BusUpgr")
            self._invalidar_otros(pos, excepto=proc)
            self.cache[proc][pos] = self.EstadoEnum.M
            self.tocado[proc][pos] = True
            self.memoria_valida[pos] = False
            resultado = f"Escritura P{proc+1}[{pos}]: F → M"
            return self._registrar(proc, "WRITE", pos, resultado, eventos_bus, self.EstadoEnum.M, f"Caché P{proc+1}", acierto=False)

        if hasattr(self.EstadoEnum, 'O') and estado_actual == self.EstadoEnum.O:
            eventos_bus.append("BusUpgr")
            self._invalidar_otros(pos, excepto=proc)
            self.cache[proc][pos] = self.EstadoEnum.M
            self.tocado[proc][pos] = True
            self.memoria_valida[pos] = False
            resultado = f"Escritura P{proc+1}[{pos}]: O → M"
            return self._registrar(proc, "WRITE", pos, resultado, eventos_bus, self.EstadoEnum.M, f"Caché P{proc+1}", acierto=False)

        if estado_actual == self.EstadoEnum.S:
            eventos_bus.append("BusRdX / BusUpgr")
            origen_dato = f"Caché P{proc+1}"
        elif estado_actual == self.EstadoEnum.I:
            eventos_bus.append("BusRdX")
            origen_dato = "Memoria"
            duenio_M = self._hay_modificado(pos, excepto=proc)
            if duenio_M is not None:
                eventos_bus.append("Flush")
                origen_dato = f"Caché P{duenio_M+1}"
                self.cache[duenio_M][pos] = self.EstadoEnum.I
                self.tocado[duenio_M][pos] = True
            elif hasattr(self.EstadoEnum, 'O'):
                duenio_O = self._hay_owned(pos, excepto=proc)
                if duenio_O is not None:
                    eventos_bus.append("Flush")
                    origen_dato = f"Caché P{duenio_O+1} (Owned)"
                    self.cache[duenio_O][pos] = self.EstadoEnum.I
                    self.tocado[duenio_O][pos] = True

        self._invalidar_otros(pos, excepto=proc)
        self.cache[proc][pos] = self.EstadoEnum.M
        self.tocado[proc][pos] = True
        self.memoria_valida[pos] = False
        resultado = f"Escritura P{proc+1}[{pos}]: {estado_actual.value} → M"
        return self._registrar(proc, "WRITE", pos, resultado, eventos_bus, self.EstadoEnum.M, origen_dato, acierto=False)

    def _registrar(self, proc, op, pos, resultado, bus, nuevo_estado, origen, acierto):
        bus_str = ", ".join(bus) if bus else "—"
        evento = {
            "proc": proc, "op": op, "pos": pos, "resultado": resultado,
            "bus": bus_str, "origen": origen, "acierto": acierto,
            "estado_final": nuevo_estado.value,
            "snapshot": {p: {pos2: self.cache[p][pos2].value for pos2 in self.posiciones} for p in range(self.num_procesadores)},
        }
        self.historial.append(evento)
        return evento
