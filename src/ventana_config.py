import customtkinter as ctk
from src.constantes import *

class VentanaConfig(ctk.CTkToplevel):
    def __init__(self, parent, num_proc_actual, num_bloques_actual, callback):
        super().__init__(parent)
        self.title("Configuración")
        self.geometry("360x280")
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)
        self.transient(parent)
        self.after(100, self.grab_set)

        self.callback = callback
        self.num_proc = num_proc_actual
        self.num_bloq = num_bloques_actual
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="⚙  CONFIGURACIÓN",
            font=ctk.CTkFont(family="monospace", size=13, weight="bold"),
            text_color=ACCENT2
        ).pack(anchor="w", padx=24, pady=(20, 10))

        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=24, pady=(0, 16))

        self._fila_contador(
            label="Procesadores",
            getter=lambda: self.num_proc,
            setter=lambda v: setattr(self, 'num_proc', v),
            minimo=2, maximo=8, hint="(2 – 8)"
        )
        self._fila_contador(
            label="Bloques de memoria",
            getter=lambda: self.num_bloq,
            setter=lambda v: setattr(self, 'num_bloq', v),
            minimo=2, maximo=8, hint="(2 – 8)"
        )

        ctk.CTkLabel(
            self, text="⚠  Cambiar la configuración reseteará la simulación.",
            font=ctk.CTkFont(size=11), text_color=WARNING
        ).pack(pady=(4, 14))

        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(fill="x", padx=24, pady=(0, 14))

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
