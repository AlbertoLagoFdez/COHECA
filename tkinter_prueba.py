#!/usr/bin/env python3
"""
Simulador de Protocolos de Coherencia de Caché
Protocolos: MSI, MESI, MESIF, MOESI
GUI: CustomTkinter
"""

import customtkinter as ctk
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

ESTADO_COLORES = {
    "I": "#555566", "S": "#4A9EFF", "E": "#4ADE80",
    "M": "#FF5566", "F": "#C084FC", "O": "#FBBF24", "-": "#333344",
}
ESTADO_TEXTO = {
    "I": "#AAAACC", "S": "#DDEEFF", "E": "#DDFFEE",
    "M": "#FFDDEE", "F": "#F0DDFF", "O": "#FFF3DD", "-": "#666677",
}

LETRAS_DISPONIBLES = ["A","B","C","D","E","F","G","H"]

# ─────────────────────────────────────────────
#  Colores globales (necesarios antes de VentanaConfig)
# ─────────────────────────────────────────────

BG_MAIN     = "#0F0F1A"
BG_PANEL    = "#161625"
BG_CARD     = "#1E1E30"
BG_HEADER   = "#12122A"
ACCENT      = "#6366F1"
ACCENT2     = "#818CF8"
TEXT_BRIGHT = "#E8E8FF"
TEXT_DIM    = "#8888AA"
BORDER      = "#2A2A45"
SUCCESS     = "#4ADE80"
DANGER      = "#FF5566"
WARNING     = "#FBBF24"

# ─────────────────────────────────────────────
#  Lógica del Simulador
# ─────────────────────────────────────────────

class Simulador:
    def __init__(self, protocolo="MSI", num_procesadores=3, posiciones=None):
        self.protocolo = protocolo.upper()
        self.num_procesadores = num_procesadores
        self.posiciones = posiciones or ["A","B","C","D"]
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

# ─────────────────────────────────────────────
#  Ventana de Configuración
# ─────────────────────────────────────────────

class VentanaConfig(ctk.CTkToplevel):
    def __init__(self, parent, num_proc_actual, num_bloques_actual, callback):
        super().__init__(parent)
        self.title("Configuración")
        self.geometry("360x280")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)
        self.transient(parent)   # asociada a la ventana principal
        self.after(100, self.grab_set)  # modal: espera a que la ventana sea visible

        self.callback = callback
        self.num_proc = num_proc_actual
        self.num_bloq = num_bloques_actual
        self._build()

    def _build(self):
        # Título
        ctk.CTkLabel(
            self, text="⚙  CONFIGURACIÓN",
            font=ctk.CTkFont(family="monospace", size=13, weight="bold"),
            text_color=ACCENT2
        ).pack(anchor="w", padx=24, pady=(20, 10))

        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=24, pady=(0, 16))

        # ── Fila procesadores ──
        self._fila_contador(
            label="Procesadores",
            getter=lambda: self.num_proc,
            setter=lambda v: setattr(self, 'num_proc', v),
            minimo=2, maximo=8,
            hint="(2 – 8)"
        )

        # ── Fila bloques ──
        self._fila_contador(
            label="Bloques de memoria",
            getter=lambda: self.num_bloq,
            setter=lambda v: setattr(self, 'num_bloq', v),
            minimo=2, maximo=8,
            hint="(2 – 8)"
        )

        # Aviso
        ctk.CTkLabel(
            self, text="⚠  Cambiar la configuración reseteará la simulación.",
            font=ctk.CTkFont(size=11), text_color=WARNING
        ).pack(pady=(4, 14))

        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=24, pady=(0, 14))

        # Botones
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=24)
        btns.columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btns, text="Cancelar", command=self.destroy,
            fg_color=BG_CARD, hover_color=BORDER,
            text_color=TEXT_DIM, height=36, corner_radius=8,
            font=ctk.CTkFont(size=13)
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            btns, text="Guardar y aplicar", command=self._guardar,
            fg_color=ACCENT, hover_color=ACCENT2,
            text_color=TEXT_BRIGHT, height=36, corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def _fila_contador(self, label, getter, setter, minimo, maximo, hint):
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=24, pady=(0, 10))

        ctk.CTkLabel(
            fila, text=label,
            font=ctk.CTkFont(size=13), text_color=TEXT_BRIGHT, width=150, anchor="w"
        ).pack(side="left")

        lbl_val = ctk.CTkLabel(
            fila, text=str(getter()),
            font=ctk.CTkFont(family="monospace", size=15, weight="bold"),
            text_color=ACCENT2, width=36
        )

        def decrementar():
            nuevo = max(minimo, getter() - 1)
            setter(nuevo)
            lbl_val.configure(text=str(nuevo))

        def incrementar():
            nuevo = min(maximo, getter() + 1)
            setter(nuevo)
            lbl_val.configure(text=str(nuevo))

        ctk.CTkButton(fila, text="−", width=32, height=32,
                      fg_color=BG_CARD, hover_color=BORDER, text_color=TEXT_BRIGHT,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=decrementar).pack(side="left", padx=(0, 6))
        lbl_val.pack(side="left")
        ctk.CTkButton(fila, text="+", width=32, height=32,
                      fg_color=BG_CARD, hover_color=BORDER, text_color=TEXT_BRIGHT,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=incrementar).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(fila, text=hint, font=ctk.CTkFont(size=11),
                     text_color=TEXT_DIM).pack(side="left", padx=(10, 0))

    def _guardar(self):
        self.callback(self.num_proc, self.num_bloq)
        self.destroy()


# ─────────────────────────────────────────────
#  GUI principal
# ─────────────────────────────────────────────

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de Coherencia de Caché")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(fg_color=BG_MAIN)

        self.sim = Simulador("MSI", num_procesadores=3, posiciones=["A","B","C","D"])
        self._ventana_config_abierta = None
        self._build_ui()
        self._actualizar_tabla()

    def _build_ui(self):
        # ── Header ──────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=BG_HEADER, corner_radius=0, height=56)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⬡  SIMULADOR DE COHERENCIA DE CACHÉ",
            font=ctk.CTkFont(family="monospace", size=15, weight="bold"),
            text_color=ACCENT2
        ).pack(side="left", padx=24)

        # Botón configuración
        ctk.CTkButton(
            header, text="⚙  Config", command=self._abrir_config,
            fg_color=BG_CARD, hover_color=BORDER,
            font=ctk.CTkFont(size=12), text_color=TEXT_DIM,
            width=90, height=32, corner_radius=8
        ).pack(side="right", padx=(8, 20))

        # Selector protocolo
        proto_frame = ctk.CTkFrame(header, fg_color="transparent")
        proto_frame.pack(side="right", padx=(0, 4))
        ctk.CTkLabel(proto_frame, text="Protocolo:", font=ctk.CTkFont(size=12), text_color=TEXT_DIM).pack(side="left", padx=(0,8))
        self.proto_var = ctk.StringVar(value="MSI")
        ctk.CTkOptionMenu(
            proto_frame, values=["MSI", "MESI", "MESIF", "MOESI"],
            variable=self.proto_var, command=self._cambiar_protocolo,
            fg_color=BG_CARD, button_color=ACCENT, button_hover_color=ACCENT2,
            dropdown_fg_color=BG_CARD, font=ctk.CTkFont(family="monospace", size=13, weight="bold"),
            text_color=TEXT_BRIGHT, width=110
        ).pack(side="left")

        # ── Layout principal ─────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(12,16))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0,10))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=0)
        right.rowconfigure(1, weight=0)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        # ── Panel operación ──────────────────────────
        ctrl = ctk.CTkFrame(left, fg_color=BG_PANEL, corner_radius=12)
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(ctrl, text="OPERACIÓN", font=ctk.CTkFont(family="monospace", size=11, weight="bold"),
                     text_color=TEXT_DIM).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(12,6))

        ctk.CTkLabel(ctrl, text="Procesador", font=ctk.CTkFont(size=12), text_color=TEXT_DIM
                     ).grid(row=1, column=0, padx=(16,8), pady=4, sticky="w")
        self.proc_var = ctk.StringVar(value="P1")
        self.proc_menu = ctk.CTkOptionMenu(
            ctrl, values=self._lista_procesadores(), variable=self.proc_var,
            fg_color=BG_CARD, button_color=ACCENT, button_hover_color=ACCENT2,
            dropdown_fg_color=BG_CARD, font=ctk.CTkFont(family="monospace", size=13),
            text_color=TEXT_BRIGHT, width=90)
        self.proc_menu.grid(row=1, column=1, padx=4, pady=4)

        ctk.CTkLabel(ctrl, text="Bloque", font=ctk.CTkFont(size=12), text_color=TEXT_DIM
                     ).grid(row=1, column=2, padx=(12,8), pady=4, sticky="w")
        self.pos_var = ctk.StringVar(value=self.sim.posiciones[0])
        self.pos_menu = ctk.CTkOptionMenu(
            ctrl, values=self.sim.posiciones, variable=self.pos_var,
            fg_color=BG_CARD, button_color=ACCENT, button_hover_color=ACCENT2,
            dropdown_fg_color=BG_CARD, font=ctk.CTkFont(family="monospace", size=13),
            text_color=TEXT_BRIGHT, width=80)
        self.pos_menu.grid(row=1, column=3, padx=(4,16), pady=4)

        btn_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=4, padx=16, pady=(6,14), sticky="ew")
        btn_frame.columnconfigure((0,1,2), weight=1)

        ctk.CTkButton(btn_frame, text="📖  LEER", command=self._leer,
                      fg_color="#1A3A5C", hover_color="#1E4A72",
                      font=ctk.CTkFont(family="monospace", size=13, weight="bold"),
                      text_color="#4A9EFF", height=38, corner_radius=8
                      ).grid(row=0, column=0, padx=(0,6), sticky="ew")

        ctk.CTkButton(btn_frame, text="✏️  ESCRIBIR", command=self._escribir,
                      fg_color="#3A1A1A", hover_color="#4A2020",
                      font=ctk.CTkFont(family="monospace", size=13, weight="bold"),
                      text_color="#FF5566", height=38, corner_radius=8
                      ).grid(row=0, column=1, padx=6, sticky="ew")

        ctk.CTkButton(btn_frame, text="↺  RESET", command=self._reset,
                      fg_color=BG_CARD, hover_color="#2A2A45",
                      font=ctk.CTkFont(family="monospace", size=13, weight="bold"),
                      text_color=TEXT_DIM, height=38, corner_radius=8
                      ).grid(row=0, column=2, padx=(6,0), sticky="ew")

        # ── Tabla caché ──────────────────────────────
        tabla_outer = ctk.CTkFrame(left, fg_color=BG_PANEL, corner_radius=12)
        tabla_outer.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(tabla_outer, text="ESTADOS DE CACHÉ",
                     font=ctk.CTkFont(family="monospace", size=11, weight="bold"),
                     text_color=TEXT_DIM).pack(anchor="w", padx=16, pady=(12,8))
        self.tabla_frame = ctk.CTkFrame(tabla_outer, fg_color="transparent")
        self.tabla_frame.pack(fill="both", expand=True, padx=16, pady=(0,16))

        # ── Panel derecho ────────────────────────────
        bus_card = ctk.CTkFrame(right, fg_color=BG_PANEL, corner_radius=12)
        bus_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(bus_card, text="ÚLTIMO EVENTO DE BUS",
                     font=ctk.CTkFont(family="monospace", size=11, weight="bold"),
                     text_color=TEXT_DIM).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12,6))
        self.lbl_op     = self._info_row(bus_card, "Operación", 1)
        self.lbl_bus    = self._info_row(bus_card, "Bus", 2)
        self.lbl_origen = self._info_row(bus_card, "Origen dato", 3)
        self.lbl_result = self._info_row(bus_card, "Resultado", 4, last=True)

        self._build_leyenda_panel(right)

        hist_outer = ctk.CTkFrame(right, fg_color=BG_PANEL, corner_radius=12)
        hist_outer.grid(row=2, column=0, sticky="nsew")
        hist_outer.rowconfigure(1, weight=1)
        hist_outer.columnconfigure(0, weight=1)
        ctk.CTkLabel(hist_outer, text="HISTORIAL",
                     font=ctk.CTkFont(family="monospace", size=11, weight="bold"),
                     text_color=TEXT_DIM).grid(row=0, column=0, sticky="w", padx=16, pady=(12,4))
        self.historial_text = ctk.CTkTextbox(
            hist_outer, fg_color=BG_CARD, text_color=TEXT_DIM,
            font=ctk.CTkFont(family="monospace", size=11),
            corner_radius=8, border_width=0, wrap="word")
        self.historial_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0,12))
        self.historial_text.configure(state="disabled")

    # ── Ventana configuración ────────────────────

    def _abrir_config(self):
        if self._ventana_config_abierta is not None and self._ventana_config_abierta.winfo_exists():
            self._ventana_config_abierta.focus()
            return
        self._ventana_config_abierta = VentanaConfig(
            self,
            num_proc_actual=self.sim.num_procesadores,
            num_bloques_actual=len(self.sim.posiciones),
            callback=self._aplicar_config
        )

    def _aplicar_config(self, num_proc, num_bloq):
        nuevas_posiciones = LETRAS_DISPONIBLES[:num_bloq]
        self.sim.reconfigurar(num_proc, nuevas_posiciones)
        self.proc_menu.configure(values=self._lista_procesadores())
        self.proc_var.set("P1")
        self.pos_menu.configure(values=nuevas_posiciones)
        self.pos_var.set(nuevas_posiciones[0])
        self._reset()

    def _lista_procesadores(self):
        return [f"P{i+1}" for i in range(self.sim.num_procesadores)]

    # ── Helpers UI ───────────────────────────────

    def _build_leyenda_panel(self, parent):
        leyenda_outer = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=12)
        leyenda_outer.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(leyenda_outer, text="LEYENDA",
                     font=ctk.CTkFont(family="monospace", size=11, weight="bold"),
                     text_color=TEXT_DIM).pack(anchor="w", padx=16, pady=(10,4))
        self.leyenda_frame = ctk.CTkFrame(leyenda_outer, fg_color="transparent")
        self.leyenda_frame.pack(fill="x", padx=12, pady=(0,10))
        self._actualizar_leyenda()

    def _actualizar_leyenda(self):
        for w in self.leyenda_frame.winfo_children():
            w.destroy()
        estados_protocolo = {
            "MSI":   [("M","Modificado"), ("S","Compartido"), ("I","Inválido")],
            "MESI":  [("M","Modificado"), ("E","Exclusivo"), ("S","Compartido"), ("I","Inválido")],
            "MESIF": [("M","Modificado"), ("E","Exclusivo"), ("S","Compartido"), ("I","Inválido"), ("F","Forward")],
            "MOESI": [("M","Modificado"), ("O","Owned"), ("E","Exclusivo"), ("S","Compartido"), ("I","Inválido")],
        }
        for letra, desc in estados_protocolo.get(self.sim.protocolo, []):
            row = ctk.CTkFrame(self.leyenda_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            chip = ctk.CTkFrame(row, fg_color=ESTADO_COLORES.get(letra, "#444"), width=28, height=22, corner_radius=4)
            chip.pack(side="left", padx=(0,8))
            chip.pack_propagate(False)
            ctk.CTkLabel(chip, text=letra, font=ctk.CTkFont(family="monospace", size=11, weight="bold"),
                         text_color=ESTADO_TEXTO.get(letra, "white")).pack(expand=True)
            ctk.CTkLabel(row, text=desc, font=ctk.CTkFont(size=11), text_color=TEXT_DIM).pack(side="left")

    def _info_row(self, parent, label, row, last=False):
        ctk.CTkLabel(parent, text=label + ":", font=ctk.CTkFont(size=11), text_color=TEXT_DIM,
                     width=90, anchor="w").grid(row=row, column=0, padx=(16,4), pady=(2, 10 if last else 2), sticky="w")
        lbl = ctk.CTkLabel(parent, text="—", font=ctk.CTkFont(family="monospace", size=12),
                           text_color=TEXT_BRIGHT, anchor="w", wraplength=200)
        lbl.grid(row=row, column=1, padx=(0,16), pady=(2, 10 if last else 2), sticky="w")
        return lbl

    def _actualizar_tabla(self):
        for w in self.tabla_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.tabla_frame, text="Bloque",
                     font=ctk.CTkFont(family="monospace", size=12, weight="bold"),
                     text_color=TEXT_DIM, width=60).grid(row=0, column=0, padx=4, pady=4)
        for p in range(self.sim.num_procesadores):
            ctk.CTkLabel(self.tabla_frame, text=f"P{p+1}",
                         font=ctk.CTkFont(family="monospace", size=14, weight="bold"),
                         text_color=ACCENT2, width=80).grid(row=0, column=p+1, padx=4, pady=4)
        sep = ctk.CTkFrame(self.tabla_frame, fg_color=BORDER, height=1)
        sep.grid(row=1, column=0, columnspan=self.sim.num_procesadores+1, sticky="ew", pady=2)
        for i, pos in enumerate(self.sim.posiciones):
            ctk.CTkLabel(self.tabla_frame, text=pos,
                         font=ctk.CTkFont(family="monospace", size=14, weight="bold"),
                         text_color=TEXT_BRIGHT, width=60).grid(row=i+2, column=0, padx=4, pady=6)
            for p in range(self.sim.num_procesadores):
                estado = self.sim.cache[p][pos]
                tocado = self.sim.tocado[p][pos]
                val = estado.value
                if val == "I" and not tocado:
                    display, color_bg, color_txt = "—", ESTADO_COLORES["-"], ESTADO_TEXTO["-"]
                else:
                    display = val
                    color_bg = ESTADO_COLORES.get(val, "#444")
                    color_txt = ESTADO_TEXTO.get(val, "white")
                chip = ctk.CTkFrame(self.tabla_frame, fg_color=color_bg, width=64, height=36, corner_radius=8)
                chip.grid(row=i+2, column=p+1, padx=8, pady=4)
                chip.grid_propagate(False)
                ctk.CTkLabel(chip, text=display,
                             font=ctk.CTkFont(family="monospace", size=16, weight="bold"),
                             text_color=color_txt).place(relx=0.5, rely=0.5, anchor="center")

    def _actualizar_bus_panel(self, evento):
        op_str = "LECTURA" if evento["op"] == "READ" else "ESCRITURA"
        color_op = "#4A9EFF" if evento["op"] == "READ" else DANGER
        self.lbl_op.configure(text=f"P{evento['proc']+1} — {op_str} [{evento['pos']}]", text_color=color_op)
        self.lbl_bus.configure(text=evento["bus"], text_color=WARNING if evento["bus"] != "—" else TEXT_DIM)
        self.lbl_origen.configure(text=evento["origen"], text_color=TEXT_BRIGHT)
        self.lbl_result.configure(text=evento["resultado"], text_color=SUCCESS if evento["acierto"] else WARNING)

    def _actualizar_historial(self):
        self.historial_text.configure(state="normal")
        self.historial_text.delete("1.0", "end")
        for i, ev in enumerate(reversed(self.sim.historial), 1):
            n = len(self.sim.historial) - i + 1
            op = "RD" if ev["op"] == "READ" else "WR"
            simbolo = "✓" if ev["acierto"] else "→"
            self.historial_text.insert("end", f"#{n:02d}  P{ev['proc']+1} {op} [{ev['pos']}]  {simbolo}  Bus: {ev['bus']}\n")
        self.historial_text.configure(state="disabled")

    def _leer(self):
        proc = int(self.proc_var.get()[1]) - 1
        ev = self.sim.leer(proc, self.pos_var.get())
        self._actualizar_tabla(); self._actualizar_bus_panel(ev); self._actualizar_historial()

    def _escribir(self):
        proc = int(self.proc_var.get()[1]) - 1
        ev = self.sim.escribir(proc, self.pos_var.get())
        self._actualizar_tabla(); self._actualizar_bus_panel(ev); self._actualizar_historial()

    def _reset(self):
        self.sim.resetear()
        self.lbl_op.configure(text="—", text_color=TEXT_BRIGHT)
        self.lbl_bus.configure(text="—", text_color=TEXT_DIM)
        self.lbl_origen.configure(text="—", text_color=TEXT_BRIGHT)
        self.lbl_result.configure(text="—", text_color=TEXT_BRIGHT)
        self.historial_text.configure(state="normal")
        self.historial_text.delete("1.0", "end")
        self.historial_text.configure(state="disabled")
        self._actualizar_tabla()

    def _cambiar_protocolo(self, protocolo):
        self.sim.cambiar_protocolo(protocolo)
        self._reset()
        self._actualizar_leyenda()


if __name__ == "__main__":
    app = App()
    app.mainloop()