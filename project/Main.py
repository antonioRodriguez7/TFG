from CircuitAnalyzer import CircuitAnalyzer
from GroverEngine import GroverEngine
from Visualizer import Visualizer


class MainApp:

    def run(self):

        analyzer = CircuitAnalyzer()
        params = analyzer.obtener_parametros_desde_qasm()

        if params is None:
            return

        n, number, choice = params

        print("Número de qubits:", n)
        print("Número objetivo:", number)
        print("Oráculo elegido:", choice)

        engine = GroverEngine()
        states, labels, choice = engine.analyze_grover(n, number, choice)

        if not states:
            print("No hay estados para graficar.")
            return

        visualizer = Visualizer()
        visualizer.plot_grover_step_by_step(states, labels, n, number, choice)


if __name__ == "__main__":
    app = MainApp()
    app.run()