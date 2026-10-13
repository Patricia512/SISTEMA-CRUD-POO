"""
views.py
========
CONTROLADORES del sistema académico.

  CrudBase                -> clase abstracta con el CRUD escrito UNA sola vez
  EstudianteController    -> carnet único
  DocenteController       -> email único
  MateriaController       -> código único, docente existente
  MatriculaController     -> reglas de matrícula, notas y boletín
  reporte(...)            -> reportes polimórficos
"""

from abc import ABC, abstractmethod

from models import Estudiante, Docente, Materia, Matricula
from shared.json_manager import GestorJSON


# =====================================================================
# CLASE BASE (ABSTRACTA): el CRUD se escribe una sola vez aquí
# =====================================================================
class CrudBase(ABC):

    # ---- CONFIGURACION: cada hijo la redefine ----
    MODELO = None              # clase del modelo (Estudiante, Docente...)
    ARCHIVO = ""               # ruta del JSON
    NOMBRE = ""                # nombre en singular, para titulos del menu
    CAMPOS_BUSCABLES = ()      # atributos donde busca buscar()

    def __init__(self, archivo=None):
        self.__gestor = GestorJSON(archivo or self.ARCHIVO)
        # ENCAPSULAMIENTO: la lista es privada; hacia afuera sale como copia
        self.__lista = [self.MODELO.desde_diccionario(datos)
                        for datos in self.__gestor.leer()]

    # ---------- lo que el menu consulta (sin conocer el modelo) ----------
    @property
    def nombre(self):
        return self.NOMBRE

    @property
    def campos(self):
        return self.MODELO.CAMPOS

    # ---------- CONTRATO: cada hijo escribe sus reglas ----------
    @abstractmethod
    def validar(self, datos, id_actual=None):
        """Devuelve None si todo esta bien, o un texto con el error.
        id_actual es None al crear y el id del registro al actualizar."""

    # ---------- GANCHO opcional ----------
    def preparar(self, datos):
        """Permite ajustar los datos antes de construir el objeto."""
        return datos

    # ---------- ayuda reutilizable para los validar() ----------
    def validar_obligatorios(self, datos):
        faltantes = [campo for campo in self.MODELO.OBLIGATORIOS
                     if not str(datos.get(campo, "")).strip()]
        if faltantes:
            return f"Faltan campos obligatorios: {', '.join(faltantes)}"
        return None

    # ---------- persistencia ----------
    def guardar(self):
        return self.__gestor.guardar([objeto.a_diccionario() for objeto in self.__lista])

    # ---------- consultas ----------
    def listar(self):
        return tuple(self.__lista)               # copia de solo lectura

    def registros(self):
        """Lista de diccionarios (util para validar unicidad)."""
        return [objeto.a_diccionario() for objeto in self.__lista]

    def obtener(self, id_registro):
        for objeto in self.__lista:
            if objeto.id == id_registro:
                return objeto
        return None

    def existe(self, id_registro):
        return self.obtener(id_registro) is not None

    def siguiente(self):
        return max((objeto.id for objeto in self.__lista), default=0) + 1

    def buscar(self, texto):
        texto = str(texto).strip().lower()
        if texto == "":
            return []
        return [objeto for objeto in self.__lista
                if any(texto in str(getattr(objeto, campo)).lower()
                       for campo in self.CAMPOS_BUSCABLES)]

    # ---------- operaciones (todas devuelven (exito, mensaje)) ----------
    def crear(self, datos):
        try:
            error = self.validar(datos)
            if error:
                return False, error

            datos = self.preparar(datos)
            valores = {campo: datos.get(campo, "") for campo in self.MODELO.CAMPOS}
            valores["id"] = self.siguiente()
            objeto = self.MODELO.desde_diccionario(valores)
        except ValueError as error:           # el modelo se protege solo
            return False, str(error)
        
        self.__lista.append(objeto)
        if not self.guardar():
            self.__lista.remove(objeto)
            return False, "No se pudo guardar el archivo"
        return True, f"Se creo {self.NOMBRE}: {objeto.etiqueta()}"

    def actualizar(self, id_registro, cambios):
        if not cambios:
            return False, "No se indico ningun cambio"

        objeto = self.obtener(id_registro)
        if objeto is None:
            return False, f"No existe {self.NOMBRE} con id {id_registro}"

        try:
            error = self.validar(cambios, id_actual=id_registro)
            if error:
                return False, error

            # Se construye un objeto NUEVO con los cambios: si algo falla,
            # el objeto viejo queda intacto.
            datos = objeto.a_diccionario()
            datos.update(cambios)
            datos["id"] = objeto.id
            nuevo = self.MODELO.desde_diccionario(datos)
        except ValueError as error:
            return False, str(error)

        self.__lista[self.__lista.index(objeto)] = nuevo
        self.guardar()
        return True, f"Se actualizo {self.NOMBRE} {id_registro}"

    def eliminar(self, id_registro):
        objeto = self.obtener(id_registro)
        if objeto is None:
            return False, f"No existe {self.NOMBRE} con id {id_registro}"

        self.__lista.remove(objeto)
        self.guardar()
        return True, f"Se elimino {self.NOMBRE} {id_registro}"


# =====================================================================
# CONTROLADOR DE ESTUDIANTE
# =====================================================================
class EstudianteController(CrudBase):

    MODELO = Estudiante
    ARCHIVO = "data/estudiantes.json"
    NOMBRE = "estudiante"
    CAMPOS_BUSCABLES = ("nombre", "apellido", "email", "carnet")

    def validar(self, datos, id_actual=None):
        if id_actual is None:
            error = self.validar_obligatorios(datos)
            if error:
                return error

        # Carnet unico
        if "carnet" in datos and str(datos["carnet"]).strip():
            carnet = str(datos["carnet"]).strip().upper()
            usados = {r["carnet"].upper() for r in self.registros()
                      if r["id"] != id_actual}
            if carnet in usados:
                return f"El carnet {carnet} ya esta registrado"
        return None


# =====================================================================
# CONTROLADOR DE DOCENTE
# =====================================================================
class DocenteController(CrudBase):

    MODELO = Docente
    ARCHIVO = "data/docentes.json"
    NOMBRE = "docente"
    CAMPOS_BUSCABLES = ("nombre", "apellido", "email", "especialidad")

    def validar(self, datos, id_actual=None):
        if id_actual is None:
            error = self.validar_obligatorios(datos)
            if error:
                return error

        # Email unico (el modelo lo guarda en minusculas)
        if "email" in datos and str(datos["email"]).strip():
            email = str(datos["email"]).strip().lower()
            usados = {r["email"] for r in self.registros()
                      if r["id"] != id_actual}
            if email in usados:
                return "Ese email ya esta registrado"
        return None


# =====================================================================
# CONTROLADOR DE MATERIA
# =====================================================================
class MateriaController(CrudBase):

    MODELO = Materia
    ARCHIVO = "data/materias.json"
    NOMBRE = "materia"
    CAMPOS_BUSCABLES = ("nombre", "codigo")

    def __init__(self, docentes=None, archivo=None):
        super().__init__(archivo)
        # Se reciben los MISMOS docentes que usa el menu (como VentaController)
        self.docentes = docentes if docentes is not None else DocenteController()

    def validar(self, datos, id_actual=None):
        # 1. Obligatorios al crear
        if id_actual is None:
            error = self.validar_obligatorios(datos)
            if error:
                return error

        # 2. Codigo unico
        if "codigo" in datos and str(datos["codigo"]).strip():
            codigo = str(datos["codigo"]).strip().upper()
            usados = {r["codigo"].upper() for r in self.registros()
                      if r["id"] != id_actual}
            if codigo in usados:
                return f"El codigo {codigo} ya esta registrado"

        # 3. Si viene docente_id (y no es vacio), ese docente debe existir
        if "docente_id" in datos and str(datos["docente_id"]).strip() not in ("", "0", "None"):
            try:
                docente_id = int(datos["docente_id"])
            except (TypeError, ValueError):
                return f"docente_id invalido: '{datos['docente_id']}'"
            if not self.docentes.existe(docente_id):
                return f"No existe un docente con id {docente_id}"
        return None

    # --- metodos propios ---
    def asignar_docente(self, materia_id, docente_id):
        if not self.existe(materia_id):
            return False, f"No existe materia con id {materia_id}"
        try:
            docente_id = int(docente_id)
        except (TypeError, ValueError):
            return False, f"docente_id invalido: '{docente_id}'"
        if not self.docentes.existe(docente_id):
            return False, f"No existe un docente con id {docente_id}"
        return self.actualizar(materia_id, {"docente_id": docente_id})

    def materias_de_docente(self, docente_id):
        return [m for m in self.listar() if m.docente_id == docente_id]


# =====================================================================
# CONTROLADOR DE MATRICULA
# =====================================================================
class MatriculaController(CrudBase):
    """El equivalente academico del VentaController."""

    MODELO = Matricula
    ARCHIVO = "data/matriculas.json"
    NOMBRE = "matricula"
    CAMPOS_BUSCABLES = ("periodo",)
    PERIODO_POR_DEFECTO = "2026-1"      # el mismo que usa el modelo

    def __init__(self, estudiantes=None, materias=None, archivo=None):
        super().__init__(archivo)
        self.estudiantes = estudiantes if estudiantes is not None else EstudianteController()
        self.materias = materias if materias is not None else MateriaController()

    def validar(self, datos, id_actual=None):
        actual = self.obtener(id_actual) if id_actual is not None else None

        if actual is None:
            error = self.validar_obligatorios(datos)
            if error:
                return error

        # Valores finales: lo que viene en datos, o lo que ya tenia la matricula
        try:
            estudiante_id = int(datos.get("estudiante_id",
                                          actual.estudiante_id if actual else ""))
            materia_id = int(datos.get("materia_id",
                                       actual.materia_id if actual else ""))
        except (TypeError, ValueError):
            return "estudiante_id y materia_id deben ser numeros"
        periodo = (str(datos.get("periodo", actual.periodo if actual else "")).strip()
                   or self.PERIODO_POR_DEFECTO)

        # 1. El estudiante debe existir
        if not self.estudiantes.existe(estudiante_id):
            return f"No existe un estudiante con id {estudiante_id}"
        # 2. La materia debe existir
        if not self.materias.existe(materia_id):
            return f"No existe una materia con id {materia_id}"
        # 3. Sin matriculas repetidas (mismo estudiante + materia + periodo)
        for otra in self.listar():
            if (otra.id != id_actual
                    and otra.estudiante_id == estudiante_id
                    and otra.materia_id == materia_id
                    and otra.periodo == periodo):
                return (f"El estudiante {estudiante_id} ya esta matriculado "
                        f"en la materia {materia_id} en el periodo {periodo}")
        return None

    # --- metodos propios ---
    def agregar_nota(self, matricula_id, tipo, valor, peso=1):  # indica cuanto vale la nota dentro del promedio.
        """Mismo patron que la venta: obtener, usar su metodo,
        atrapar ValueError y guardar el archivo completo."""
        matricula = self.obtener(matricula_id)
        if matricula is None:
            return False, f"No existe matricula con id {matricula_id}"
        try:
            nota = matricula.agregar_nota(tipo, valor, peso)
        except ValueError as error:
            return False, str(error)
        self.guardar()       # sin esto la nota se pierde al cerrar el programa
        return True, (f"Nota agregada: {nota}. "
                      f"Promedio actual: {matricula.promedio} ({matricula.estado})")

    def matriculas_de_estudiante(self, estudiante_id):
        return [m for m in self.listar() if m.estudiante_id == estudiante_id]

    def boletin(self, estudiante_id):
        estudiante = self.estudiantes.obtener(estudiante_id)
        if estudiante is None:
            return None

        texto = f"BOLETIN DE {estudiante.nombre_completo}  (carnet {estudiante.carnet})\n"
        texto += "-" * 58 + "\n"

        promedios = []
        matriculas = self.matriculas_de_estudiante(estudiante_id)
        for matricula in matriculas:
            materia = self.materias.obtener(matricula.materia_id)
            nombre_materia = materia.nombre if materia else "materia eliminada"
            texto += (f"  {matricula.periodo}  {nombre_materia:<24}"
                      f"{matricula.promedio:>6.2f}  {matricula.estado}\n")
            if matricula.notas:              # las materias sin notas no cuentan
                promedios.append(matricula.promedio)

        if not matriculas:
            texto += "  (sin matriculas)\n"
        general = round(sum(promedios) / len(promedios), 2) if promedios else 0
        texto += "-" * 58 + "\n"
        texto += f"  PROMEDIO GENERAL: {general:.2f}  ({len(promedios)} materia(s) con notas)"
        return texto


# =====================================================================
# REPORTES (polimórfismo: sirven para cualquier controlador)
# =====================================================================

def reporte(controlador):
    registros = controlador.listar()
    lineas = [f"REPORTE DE {controlador.nombre.upper()}S", "-" * 50]
    for objeto in registros:
        lineas.append(f"  {objeto}")
    if not registros:
        lineas.append("  (sin registros)")
    lineas.append("-" * 50)
    lineas.append(f"  Total: {len(registros)}")
    return "\n".join(lineas)


def reporte_promedio_por_materia(matriculas):
    """Reporte a eleccion: promedio general de cada materia.
    Solo cuentan las matriculas que ya tienen notas."""
    acumulado = {}                                   # materia_id -> [promedios]
    for matricula in matriculas.listar():
        if matricula.notas:
            acumulado.setdefault(matricula.materia_id, []).append(matricula.promedio)

    lineas = ["PROMEDIO GENERAL POR MATERIA", "-" * 50]
    for materia_id, promedios in sorted(acumulado.items()):
        materia = matriculas.materias.obtener(materia_id)
        nombre = materia.nombre if materia else f"materia {materia_id} (eliminada)"
        promedio = round(sum(promedios) / len(promedios), 2)
        lineas.append(f"  {nombre:<26}{promedio:>6.2f}   ({len(promedios)} matricula(s))")
    if not acumulado:
        lineas.append("  (todavia no hay notas)")
    return "\n".join(lineas)