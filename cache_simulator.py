#!/usr/bin/env python3
"""
Simulador de Protocolos de Coherencia de Caché
Protocolos: MSI, MESI, MESIF, MOESI
Sistema: 3 procesadores con bus compartido (Snooping)
"""

import os
from enum import Enum

# ─────────────────────────────────────────────
#  Estados
# ─────────────────────────────────────────────

class EstadoMSI(Enum):
    I = "I"   # Inválido
    S = "S"   # Compartido (Shared)
    M = "M"   # Modificado

class EstadoMESI(Enum):
    I = "I"   # Inválido
    S = "S"   # Compartido (Shared)
    E = "E"   # Exclusivo
    M = "M"   # Modificado

class EstadoMESIF(Enum):
    I = "I"   # Inválido
    S = "S"   # Compartido (Shared)
    E = "E"   # Exclusivo
    M = "M"   # Modificado
    F = "F"   # Forward (designado para responder a lecturas)

class EstadoMOESI(Enum):
    I = "I"   # Inválido
    S = "S"   # Compartido (Shared)
    E = "E"   # Exclusivo
    M = "M"   # Modificado
    O = "O"   # Owned (tiene copia sucia compartida, responsable de responder)

# Colores ANSI
COLOR = {
    "I": "\033[90m",    # gris
    "S": "\033[94m",    # azul
    "E": "\033[92m",    # verde
    "M": "\033[91m",    # rojo
    "F": "\033[95m",    # magenta
    "O": "\033[93m",    # amarillo
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "YELLOW": "\033[93m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
}

NUM_PROCESADORES = 3
NUM_POSICIONES   = 4
POSICIONES       = ["A", "B", "C", "D"]

# ─────────────────────────────────────────────
#  Simulador
# ─────────────────────────────────────────────

class Simulador:
    def __init__(self, protocolo="MSI"):
        self.protocolo = protocolo.upper()
        if self.protocolo == "MSI":
            self.EstadoEnum = EstadoMSI
        elif self.protocolo == "MESI":
            self.EstadoEnum = EstadoMESI
        elif self.protocolo == "MESIF":
            self.EstadoEnum = EstadoMESIF
        elif self.protocolo == "MOESI":
            self.EstadoEnum = EstadoMOESI
        else:
            raise ValueError(f"Protocolo no válido: {protocolo}")

        self.cache = {
            p: {pos: self.EstadoEnum.I for pos in POSICIONES}
            for p in range(NUM_PROCESADORES)
        }
        self.tocado = {
            p: {pos: False for pos in POSICIONES}
            for p in range(NUM_PROCESADORES)
        }
        self.memoria_valida = {pos: True for pos in POSICIONES}
        self.historial = []

    # ── Helpers de visualización ──────────────────

    def _estado_str(self, estado, proc, pos):
        if estado == self.EstadoEnum.I and not self.tocado[proc][pos]:
            return f"{COLOR['I']}{COLOR['BOLD']}-{COLOR['RESET']}"
        c = COLOR.get(estado.value, "")
        return f"{c}{COLOR['BOLD']}{estado.value}{COLOR['RESET']}"

    # ── Helpers de consulta de estado ────────────

    def _hay_copia_valida(self, pos, excepto=None):
        for p in range(NUM_PROCESADORES):
            if p == excepto:
                continue
            if self.cache[p][pos] != self.EstadoEnum.I:
                return True
        return False

    def _hay_modificado(self, pos, excepto=None):
        for p in range(NUM_PROCESADORES):
            if p == excepto:
                continue
            if self.cache[p][pos] == self.EstadoEnum.M:
                return p
        return None

    def _hay_owned(self, pos, excepto=None):
        """MOESI: devuelve el procesador con estado O (o None)."""
        for p in range(NUM_PROCESADORES):
            if p == excepto:
                continue
            if hasattr(self.EstadoEnum, 'O') and self.cache[p][pos] == self.EstadoEnum.O:
                return p
        return None

    def _hay_forward(self, pos, excepto=None):
        """MESIF: devuelve el procesador con estado F (o None)."""
        for p in range(NUM_PROCESADORES):
            if p == excepto:
                continue
            if hasattr(self.EstadoEnum, 'F') and self.cache[p][pos] == self.EstadoEnum.F:
                return p
        return None

    def _invalidar_otros(self, pos, excepto):
        for p in range(NUM_PROCESADORES):
            if p != excepto:
                if self.cache[p][pos] != self.EstadoEnum.I:
                    self.tocado[p][pos] = True
                self.cache[p][pos] = self.EstadoEnum.I

    # ── Operación: LEER ───────────────────────────

    def leer(self, proc, pos):
        estado_actual = self.cache[proc][pos]
        eventos_bus = []
        origen_dato = "Memoria"

        # ── ACIERTO ──
        if estado_actual != self.EstadoEnum.I:
            resultado = f"  ✓ ACIERTO de lectura en P{proc+1}[{pos}] — estado: {estado_actual.value}"
            self._registrar(proc, "READ", pos, resultado, [], estado_actual, origen_dato)
            return

        # ── FALLO ── BusRd en todos los protocolos
        eventos_bus.append("BusRd")

        # ─── MSI ───────────────────────────────────────────
        if self.protocolo == "MSI":
            duenio_M = self._hay_modificado(pos, excepto=proc)
            if duenio_M is not None:
                eventos_bus.append("Flush")
                origen_dato = f"Caché P{duenio_M+1}"
                self.cache[duenio_M][pos] = self.EstadoEnum.S
                self.tocado[duenio_M][pos] = True
                self.memoria_valida[pos] = True
            nuevo_estado = self.EstadoEnum.S

        # ─── MESI ──────────────────────────────────────────
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
                eventos_bus[0] = "BusRd(S)"
                nuevo_estado = self.EstadoEnum.S
            else:
                eventos_bus[0] = "BusRd(Ŝ)"
                nuevo_estado = self.EstadoEnum.E

        # ─── MESIF ─────────────────────────────────────────
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
                # El Forward actual pasa a S; el nuevo lector se convierte en F
                forward_actual = self._hay_forward(pos, excepto=proc)
                if forward_actual is not None:
                    origen_dato = f"Caché P{forward_actual+1} (Forward)"
                    self.cache[forward_actual][pos] = self.EstadoEnum.S
                    self.tocado[forward_actual][pos] = True
                else:
                    origen_dato = "Caché (compartida)"
                nuevo_estado = self.EstadoEnum.F
            else:
                eventos_bus[0] = "BusRd(Ŝ)"
                nuevo_estado = self.EstadoEnum.E

        # ─── MOESI ─────────────────────────────────────────
        elif self.protocolo == "MOESI":
            duenio_M = self._hay_modificado(pos, excepto=proc)
            duenio_O = self._hay_owned(pos, excepto=proc)

            if duenio_M is not None:
                # M → O: el dueño mantiene la copia sucia (no escribe a memoria)
                origen_dato = f"Caché P{duenio_M+1} (Owned)"
                self.cache[duenio_M][pos] = self.EstadoEnum.O
                self.tocado[duenio_M][pos] = True
                nuevo_estado = self.EstadoEnum.S
            elif duenio_O is not None:
                # El Owned responde directamente (sin pasar por memoria)
                origen_dato = f"Caché P{duenio_O+1} (Owned)"
                nuevo_estado = self.EstadoEnum.S
            else:
                hay_otra = self._hay_copia_valida(pos, excepto=proc)
                if hay_otra:
                    nuevo_estado = self.EstadoEnum.S
                else:
                    nuevo_estado = self.EstadoEnum.E

        self.cache[proc][pos] = nuevo_estado
        self.tocado[proc][pos] = True
        resultado = f"  → Fallo de lectura P{proc+1}[{pos}]: I → {nuevo_estado.value}"
        self._registrar(proc, "READ", pos, resultado, eventos_bus, nuevo_estado, origen_dato)

    # ── Operación: ESCRIBIR ───────────────────────

    def escribir(self, proc, pos):
        estado_actual = self.cache[proc][pos]
        eventos_bus = []
        origen_dato = "—"

        # ── Acierto: ya en M ──
        if estado_actual == self.EstadoEnum.M:
            resultado = f"  ✓ ACIERTO de escritura en P{proc+1}[{pos}] — estado: M"
            self._registrar(proc, "WRITE", pos, resultado, [], estado_actual, origen_dato)
            return

        # ── E → M silencioso (MESI / MESIF / MOESI) ──
        if hasattr(self.EstadoEnum, 'E') and estado_actual == self.EstadoEnum.E:
            resultado = f"  ✓ Escritura silenciosa P{proc+1}[{pos}]: E → M (sin bus)"
            self.cache[proc][pos] = self.EstadoEnum.M
            self.tocado[proc][pos] = True
            self._registrar(proc, "WRITE", pos, resultado, [], self.EstadoEnum.M, "—")
            return

        # ── F → M (MESIF): upgrade desde Forward ──
        if hasattr(self.EstadoEnum, 'F') and estado_actual == self.EstadoEnum.F:
            eventos_bus.append("BusUpgr")
            self._invalidar_otros(pos, excepto=proc)
            self.cache[proc][pos] = self.EstadoEnum.M
            self.tocado[proc][pos] = True
            self.memoria_valida[pos] = False
            resultado = f"  → Escritura P{proc+1}[{pos}]: F → M"
            self._registrar(proc, "WRITE", pos, resultado, eventos_bus, self.EstadoEnum.M, f"Caché P{proc+1}")
            return

        # ── O → M (MOESI): el Owned escribe ──
        if hasattr(self.EstadoEnum, 'O') and estado_actual == self.EstadoEnum.O:
            eventos_bus.append("BusUpgr")
            self._invalidar_otros(pos, excepto=proc)
            self.cache[proc][pos] = self.EstadoEnum.M
            self.tocado[proc][pos] = True
            self.memoria_valida[pos] = False
            resultado = f"  → Escritura P{proc+1}[{pos}]: O → M"
            self._registrar(proc, "WRITE", pos, resultado, eventos_bus, self.EstadoEnum.M, f"Caché P{proc+1}")
            return

        # ── S → M: upgrade ──
        if estado_actual == self.EstadoEnum.S:
            eventos_bus.append("BusRdX / BusUpgr")
            origen_dato = f"Caché P{proc+1}"

        # ── I → M: fallo de escritura ──
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

        resultado = f"  → Escritura P{proc+1}[{pos}]: {estado_actual.value} → M"
        self._registrar(proc, "WRITE", pos, resultado, eventos_bus, self.EstadoEnum.M, origen_dato)

    # ── Registro e impresión ──────────────────────

    def _registrar(self, proc, op, pos, resultado, bus, nuevo_estado, origen):
        bus_str = ", ".join(bus) if bus else "—"
        evento = {
            "proc": proc,
            "op": op,
            "pos": pos,
            "resultado": resultado,
            "bus": bus_str,
            "origen": origen,
            "estado_final": {p: dict(self.cache[p]) for p in range(NUM_PROCESADORES)},
        }
        self.historial.append(evento)
        self._imprimir_evento(evento)

    def _imprimir_evento(self, ev):
        op_str = f"{COLOR['YELLOW']}{'LECTURA' if ev['op']=='READ' else 'ESCRITURA'}{COLOR['RESET']}"
        print(f"\n{COLOR['BOLD']}━━━ P{ev['proc']+1} {op_str} [{ev['pos']}] ━━━{COLOR['RESET']}")
        print(ev["resultado"])
        print(f"  Bus     : {COLOR['MAGENTA']}{ev['bus']}{COLOR['RESET']}")
        print(f"  Origen  : {COLOR['CYAN']}{ev['origen']}{COLOR['RESET']}")
        self._imprimir_tabla()

    def _imprimir_tabla(self):
        print()
        header = f"  {'Pos':>4} │"
        for p in range(NUM_PROCESADORES):
            header += f"  P{p+1}  │"
        print(f"{COLOR['BOLD']}{header}{COLOR['RESET']}")
        print("  " + "─" * (6 + 7 * NUM_PROCESADORES))
        for pos in POSICIONES:
            fila = f"  {pos:>4} │"
            for p in range(NUM_PROCESADORES):
                est = self.cache[p][pos]
                fila += f"  {self._estado_str(est, p, pos)}    │"
            print(fila)
        print()

    def imprimir_estado(self):
        print(f"\n{COLOR['BOLD']}{'═'*40}{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}  Estado actual de las cachés ({self.protocolo}){COLOR['RESET']}")
        print(f"{COLOR['BOLD']}{'═'*40}{COLOR['RESET']}")
        self._imprimir_tabla()

    def imprimir_historial(self):
        if not self.historial:
            print("  (sin operaciones registradas)")
            return
        print(f"\n{COLOR['BOLD']}{'─'*60}{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}  HISTORIAL DE OPERACIONES{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}{'─'*60}{COLOR['RESET']}")
        for i, ev in enumerate(self.historial, 1):
            op = "LEE " if ev["op"] == "READ" else "ESCR"
            print(f"  {i:>3}. P{ev['proc']+1} {op} [{ev['pos']}] | Bus: {ev['bus']:<25} | Origen: {ev['origen']}")

    def resetear(self):
        self.cache = {
            p: {pos: self.EstadoEnum.I for pos in POSICIONES}
            for p in range(NUM_PROCESADORES)
        }
        self.tocado = {
            p: {pos: False for pos in POSICIONES}
            for p in range(NUM_PROCESADORES)
        }
        self.historial = []
        print(f"  {COLOR['CYAN']}Simulador reseteado.{COLOR['RESET']}")


# ─────────────────────────────────────────────
#  Interfaz de terminal
# ─────────────────────────────────────────────

def menu_protocolo():
    print(f"\n{COLOR['BOLD']}╔══════════════════════════════════════╗{COLOR['RESET']}")
    print(f"{COLOR['BOLD']}║  Simulador de Coherencia de Caché    ║{COLOR['RESET']}")
    print(f"{COLOR['BOLD']}╚══════════════════════════════════════╝{COLOR['RESET']}")
    print("\n  Selecciona el protocolo:")
    print("  [1] MSI   — 3 estados: M, S, I")
    print("  [2] MESI  — 4 estados: M, E, S, I")
    print("  [3] MESIF — 5 estados: M, E, S, I, F (Forward)")
    print("  [4] MOESI — 5 estados: M, O, E, S, I (Owned)")
    while True:
        op = input("\n  > ").strip()
        opciones = {"1": "MSI", "2": "MESI", "3": "MESIF", "4": "MOESI"}
        if op in opciones:
            return opciones[op]
        print("  Opción no válida.")

def imprimir_leyenda(protocolo):
    print(f"\n  {COLOR['BOLD']}Leyenda de estados:{COLOR['RESET']}")
    leyenda = (
        f"   {COLOR['I']}{COLOR['BOLD']}-{COLOR['RESET']} = No accedido   "
        f"{COLOR['I']}{COLOR['BOLD']}I{COLOR['RESET']} = Inválido   "
        f"{COLOR['S']}{COLOR['BOLD']}S{COLOR['RESET']} = Compartido   "
        f"{COLOR['M']}{COLOR['BOLD']}M{COLOR['RESET']} = Modificado"
    )
    if protocolo in ("MESI", "MESIF", "MOESI"):
        leyenda += f"   {COLOR['E']}{COLOR['BOLD']}E{COLOR['RESET']} = Exclusivo"
    if protocolo == "MESIF":
        leyenda += f"   {COLOR['F']}{COLOR['BOLD']}F{COLOR['RESET']} = Forward"
    if protocolo == "MOESI":
        leyenda += f"   {COLOR['O']}{COLOR['BOLD']}O{COLOR['RESET']} = Owned"
    print(leyenda)

def menu_principal(sim):
    while True:
        print(f"\n{COLOR['BOLD']}┌─────────────────────────────────────┐{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}│  Protocolo: {sim.protocolo:<25}│{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}├─────────────────────────────────────┤{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}│  [1] Leer  (procesador + posición)  │{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}│  [2] Escribir (procesador + posición)│{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}│  [3] Ver estado actual               │{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}│  [4] Ver historial                   │{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}│  [5] Resetear simulador              │{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}│  [6] Cambiar protocolo               │{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}│  [0] Salir                           │{COLOR['RESET']}")
        print(f"{COLOR['BOLD']}└─────────────────────────────────────┘{COLOR['RESET']}")

        op = input("\n  Opción: ").strip()

        if op in ("1", "2"):
            proc = pedir_procesador()
            if proc is None:
                continue
            pos = pedir_posicion()
            if pos is None:
                continue
            if op == "1":
                sim.leer(proc, pos)
            else:
                sim.escribir(proc, pos)
        elif op == "3":
            sim.imprimir_estado()
        elif op == "4":
            sim.imprimir_historial()
        elif op == "5":
            sim.resetear()
            sim.imprimir_estado()
        elif op == "6":
            protocolo = menu_protocolo()
            sim.__init__(protocolo)
            print(f"  {COLOR['CYAN']}Protocolo cambiado a {protocolo}.{COLOR['RESET']}")
            sim.imprimir_estado()
            imprimir_leyenda(protocolo)
        elif op == "0":
            print(f"\n  {COLOR['CYAN']}¡Hasta luego!{COLOR['RESET']}\n")
            break
        else:
            print("  Opción no válida.")

def pedir_procesador():
    print(f"  Procesador (1-{NUM_PROCESADORES}): ", end="")
    try:
        p = int(input().strip()) - 1
        if 0 <= p < NUM_PROCESADORES:
            return p
    except ValueError:
        pass
    print("  Procesador no válido.")
    return None

def pedir_posicion():
    print(f"  Posición de caché ({', '.join(POSICIONES)}): ", end="")
    pos = input().strip().upper()
    if pos in POSICIONES:
        return pos
    print("  Posición no válida.")
    return None


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    protocolo = menu_protocolo()
    sim = Simulador(protocolo)
    sim.imprimir_estado()
    imprimir_leyenda(protocolo)
    menu_principal(sim)

if __name__ == "__main__":
    main()