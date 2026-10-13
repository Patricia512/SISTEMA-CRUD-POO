# main.py es la VISTA del sistema académico: lo único que habla con el usuario
# (input/print). No valida ni guarda nada: le pide todo a los controladores
# de views.py y solo muestra lo que ellos responden.
#
#   MenuCRUD(controlador)      -> un solo menú para cualquier controlador
#   MenuMatriculas(MenuCRUD)   -> hereda todo y agrega lo propio de matrículas
#   MenuPrincipal              -> crea los controladores y reparte los menús
from shared.herramientas import (
    imprimir_titulo, imprimir_exito, imprimir_error, imprimir_info, confirmar
)
from models import Nota
from views import (
    EstudianteController, DocenteController, MateriaController, MatriculaController,
    reporte, reporte_promedio_por_materia
)


# =====================================================================
# MENU GENERICO (polimorfismo por inyeccion: recibe el controlador)
# =====================================================================
class MenuCRUD:

    def __init__(self, controlador):
        self._controlador = controlador

    # ---------- ayudas ----------
    def pausa(self):
        input("\nPresione Enter para continuar...")

    def pedir_entero(self, texto):
        try:
            return int(input(texto))
        except ValueError:
            return None

    def mostrar_resultado(self, exito, mensaje):
        if exito:
            imprimir_exito(mensaje)
        else:
            imprimir_error(mensaje)

    def opciones_extra(self):
        """GANCHO: los hijos devuelven [(texto, metodo), ...] y aparecen
        como opciones 7, 8, 9... del menu."""
        return []

    # ---------- bucle del menu ----------
    def ejecutar(self):
        controlador = self._controlador
        while True:
            imprimir_titulo(controlador.nombre.upper() + "S")
            print(f"  1. Crear {controlador.nombre}")
            print("  2. Ver todos")
            print("  3. Buscar")
            print("  4. Ver por id")
            print("  5. Actualizar")
            print("  6. Eliminar")

            acciones = {"1": self.crear, "2": self.listar, "3": self.buscar,
                        "4": self.ver_por_id, "5": self.actualizar,
                        "6": self.eliminar}
            for numero, (texto, metodo) in enumerate(self.opciones_extra(), start=7):
                print(f"  {numero}. {texto}")
                acciones[str(numero)] = metodo
            print("  0. Volver\n")

            opcion = input("Opcion: ").strip()
            if opcion == "0":
                break
            accion = acciones.get(opcion)
            if accion is None:
                imprimir_error("Opcion no valida")
                self.pausa()
            else:
                accion()

    # ---------- operaciones ----------
    def crear(self):
        controlador = self._controlador
        imprimir_titulo(f"CREAR {controlador.nombre.upper()}")
        datos = {}
        for campo in controlador.campos:          # un dato por cada campo del modelo
            datos[campo] = input(f"{campo.capitalize()}: ")
        self.mostrar_resultado(*controlador.crear(datos))
        self.pausa()

    def listar(self):
        controlador = self._controlador
        imprimir_titulo(controlador.nombre.upper() + "S")
        lista = controlador.listar()
        if len(lista) == 0:
            imprimir_info("No hay registros todavia.")
        else:
            for objeto in lista:
                print(f"  {objeto}")          # POLIMORFISMO: __str__ -> etiqueta()
            imprimir_info(f"Total: {len(lista)}")
        self.pausa()

    def buscar(self):
        controlador = self._controlador
        imprimir_titulo(f"BUSCAR {controlador.nombre.upper()}")
        texto = input("Buscar: ")
        encontrados = controlador.buscar(texto)
        if len(encontrados) == 0:
            imprimir_info(f"Sin coincidencias para '{texto}'.")
        else:
            for objeto in encontrados:
                print(f"  {objeto}")
        self.pausa()

    def ver_por_id(self):
        controlador = self._controlador
        imprimir_titulo(f"VER {controlador.nombre.upper()}")
        objeto = controlador.obtener(self.pedir_entero("Id: "))
        if objeto is None:
            imprimir_error("No encontrado")
        else:
            for clave, valor in objeto.a_diccionario().items():
                print(f"  {clave.capitalize()}: {valor}")
        self.pausa()

    def actualizar(self):
        controlador = self._controlador
        imprimir_titulo(f"ACTUALIZAR {controlador.nombre.upper()}")
        id_registro = self.pedir_entero("Id: ")
        objeto = controlador.obtener(id_registro)
        if objeto is None:
            imprimir_error("No encontrado")
            self.pausa()
            return

        imprimir_info(f"Editando: {objeto.etiqueta()}")
        print("Deje en blanco lo que no quiera cambiar.\n")
        cambios = {}
        for campo in controlador.campos:
            actual = getattr(objeto, campo)
            nuevo = input(f"{campo.capitalize()} [{actual}]: ").strip()
            if nuevo != "":
                cambios[campo] = nuevo

        self.mostrar_resultado(*controlador.actualizar(id_registro, cambios))
        self.pausa()

    def eliminar(self):
        controlador = self._controlador
        imprimir_titulo(f"ELIMINAR {controlador.nombre.upper()}")
        id_registro = self.pedir_entero("Id: ")
        objeto = controlador.obtener(id_registro)
        if objeto is None:
            imprimir_error("No encontrado")
            self.pausa()
            return

        imprimir_info(f"Se eliminara: {objeto.etiqueta()}")
        if confirmar("¿Confirma?"):
            self.mostrar_resultado(*controlador.eliminar(id_registro))
        else:
            imprimir_info("Operacion cancelada")
        self.pausa()


# =====================================================================
# MENU DE MATRICULAS: HERENCIA + sobrescritura
# =====================================================================
class MenuMatriculas(MenuCRUD):

    def opciones_extra(self):
        return [("Agregar nota", self.agregar_nota),
                ("Ver boletin", self.ver_boletin)]

    def crear(self):                               # SOBRESCRIBE el crear() del padre
        controlador = self._controlador
        imprimir_titulo("MATRICULAR ESTUDIANTE")

        imprimir_info("Estudiantes:")
        for estudiante in controlador.estudiantes.listar():
            print(f"  {estudiante}")
        imprimir_info("Materias:")
        for materia in controlador.materias.listar():
            print(f"  {materia}")

        datos = {
            "estudiante_id": input("\nId del estudiante: "),
            "materia_id": input("Id de la materia: "),
            "periodo": input("Periodo (Enter = 2026-1): "),
        }
        self.mostrar_resultado(*controlador.crear(datos))
        self.pausa()

    def agregar_nota(self):
        controlador = self._controlador
        imprimir_titulo("AGREGAR NOTA")
        matricula_id = self.pedir_entero("Id de la matricula: ")
        matricula = controlador.obtener(matricula_id)
        if matricula is None:
            imprimir_error("No existe esa matricula")
            self.pausa()
            return

        imprimir_info(f"Matricula: {matricula.etiqueta()}")
        tipo = input(f"Tipo ({', '.join(Nota.TIPOS)}): ")
        valor = input(f"Valor ({Nota.MINIMA} a {Nota.MAXIMA}): ")
        peso = input("Importancia de la nota (1 = normal, 2 = vale el doble; Enter = 1): ").strip() or 1

        self.mostrar_resultado(*controlador.agregar_nota(matricula_id, tipo, valor, peso))
        self.pausa()

    def ver_boletin(self):
        imprimir_titulo("BOLETIN")
        estudiante_id = self.pedir_entero("Id del estudiante: ")
        texto = self._controlador.boletin(estudiante_id)
        if texto is None:
            imprimir_error("No existe ese estudiante")
        else:
            print(texto)
        self.pausa()


# =====================================================================
# MENU PRINCIPAL
# =====================================================================
class MenuPrincipal:

    def __init__(self):
        # UN solo controlador de cada tipo; los dependientes reciben los mismos
        self.estudiantes = EstudianteController()
        self.docentes = DocenteController()
        self.materias = MateriaController(self.docentes)
        self.matriculas = MatriculaController(self.estudiantes, self.materias)

    def pausa(self):
        input("\nPresione Enter para continuar...")

    def ejecutar(self):
        menus = {
            "1": MenuCRUD(self.estudiantes),
            "2": MenuCRUD(self.docentes),
            "3": MenuCRUD(self.materias),
            "4": MenuMatriculas(self.matriculas),
        }
        while True:
            imprimir_titulo("SISTEMA ACADEMICO")
            print("  1. Estudiantes")
            print("  2. Docentes")
            print("  3. Materias")
            print("  4. Matriculas")
            print("  5. Reportes")
            print("  0. Salir\n")
            opcion = input("Opcion: ").strip()

            if opcion in menus:
                menus[opcion].ejecutar()
            elif opcion == "5":
                self.menu_reportes()
            elif opcion == "0":
                imprimir_info("¡Hasta luego!")
                break
            else:
                imprimir_error("Opcion no valida")
                self.pausa()

    def menu_reportes(self):
        imprimir_titulo("REPORTES")
        # El MISMO reporte() sirve para los cuatro controladores
        for controlador in (self.estudiantes, self.docentes,
                            self.materias, self.matriculas):
            print(reporte(controlador))
            print()
        print(reporte_promedio_por_materia(self.matriculas))
        self.pausa()


# Solo arranca si se ejecuta "python main.py"
if __name__ == "__main__":
    try:
        MenuPrincipal().ejecutar()
    except KeyboardInterrupt:
        print("\nPrograma interrumpido por el usuario.")
