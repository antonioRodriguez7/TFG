import numpy as np
import matplotlib.pyplot as plt


class Visualizer:

    def get_solution_indices(self, choice, number, n):
        N = 2**n

        if choice == "one":
            return [number]
        elif choice == "less":
            return list(range(number))
        else:
            return list(range(number + 1, N))

    def build_grover_basis(self, n, solution_indices):
        N = 2**n

        ket_t = np.zeros(N, dtype=complex)
        for index in solution_indices:
            ket_t[index] = 1.0

        if np.linalg.norm(ket_t) > 1e-12:
            ket_t /= np.linalg.norm(ket_t)

        ket_r = np.ones(N, dtype=complex)
        for index in solution_indices:
            ket_r[index] = 0.0

        if np.linalg.norm(ket_r) > 1e-12:
            ket_r /= np.linalg.norm(ket_r)

        return ket_r, ket_t

    def project_state(self, statevector, solution_indices, n):
        amps = statevector.data

        ket_r, ket_t = self.build_grover_basis(n, solution_indices)

        c_r = np.vdot(ket_r, amps)
        c_t = np.vdot(ket_t, amps)

        if abs(c_r) > 1e-12:
            phase = np.exp(-1j * np.angle(c_r))
            c_r *= phase
            c_t *= phase

        return c_r.real, c_t.real

    def plot_grover_step_by_step(self, states, labels, n, number, choice):
        solution_indices = self.get_solution_indices(choice, number, n)

        num_plots = (len(states) - 2) // 2
        fig, axes = plt.subplots(1, num_plots, figsize=(5 * num_plots, 5))

        if num_plots == 1:
            axes = [axes]

        plot_idx = 0

        for k in range(4, len(states) + 1, 2):

            ax = axes[plot_idx]
            plot_idx += 1

            partial_states = states[:k]
            partial_labels = labels[:k]

            points = [self.project_state(s, solution_indices, n) for s in partial_states]

            xs = [p[0] for p in points]
            ys = [p[1] for p in points]

            ax.axhline(0, linewidth=1.2)
            ax.axvline(0, linewidth=1.2)

            ax.quiver(
                0, 0, 1, 0,
                angles="xy",
                scale_units="xy",
                scale=1,
                linestyle='dashed',
                color="black"
            )
            ax.text(1.05, 0, "|r⟩", fontsize=12)

            ax.quiver(
                0, 0, 0, 1,
                angles="xy",
                scale_units="xy",
                scale=1,
                linestyle='dashed',
                color="black"
            )
            ax.text(0, 1.05, "|t⟩", fontsize=12)

            for (x, y), label in zip(points[1:], partial_labels[1:]):

                color = "black"

                if "O" in label:
                    color = "red"
                elif "D" in label:
                    color = "blue"
                elif label == "|s⟩":
                    color = "green"

                ax.quiver(
                    0, 0, x, y,
                    angles="xy",
                    scale_units="xy",
                    scale=1,
                    color=color,
                    width=0.006,
                    alpha=0.85
                )

                ax.text(x + 0.04, y + 0.04, label, fontsize=9)

            ax.plot(xs, ys, linestyle="--", linewidth=2, marker="o", color="gray")

            iteracion = (k // 2) - 1
            ax.set_title(f"Iter {iteracion}")

            ax.set_xlim(-1.2, 1.2)
            ax.set_ylim(-1.2, 1.2)

            ax.set_aspect('equal')
            ax.grid(alpha=0.3)

        plt.suptitle(f"Grover paso a paso (n={n}, número={number}, tipo={choice})")

        plt.tight_layout()
        plt.show()