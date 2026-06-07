"""
Small helper to generate a PDF version of the presentation slides.

The assignment asks for a PDF document / presentation slides. This script creates
that PDF from simple slide content.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


SLIDES = [
    (
        "Problem and Goal",
        [
            "Parallel Machine Scheduling",
            "Jobs, machines, precedences, setup times and resources",
            "Goal: assign every job to a machine and a start time",
            "Objective: minimize total tardiness + makespan",
            "All Topic A constraints are treated as hard constraints",
        ],
    ),
    (
        "Algorithm Description",
        [
            "Metaheuristic: Simulated Annealing",
            "Single-solution local search method",
            "Starts from one current solution",
            "Generates one neighbour at a time",
            "Accepts better solutions",
            "Sometimes accepts worse solutions to escape local optima",
            "Temperature decreases during the search",
        ],
    ),
    (
        "Representation and Decoder",
        [
            "Representation: priority list of jobs and selected machine for each job",
            "The decoder converts this representation into real start times",
            "Only jobs whose predecessors are finished can be scheduled",
            "The decoder checks machine eligibility, setup times, precedences and resources",
            "The final solution is checked with the official validator",
        ],
    ),
    (
        "Neighbourhood and Acceptance",
        [
            "Swap two jobs in the priority list",
            "Remove and reinsert one job",
            "Change one job to another eligible machine",
            "Better neighbours are accepted",
            "Worse neighbours can be accepted depending on cost difference and temperature",
        ],
    ),
    (
        "Parameter Variants",
        [
            "short: 5000 iterations, temperature 250, cooling 0.9990",
            "default: 10000 iterations, temperature 500, cooling 0.9995",
            "hot: 10000 iterations, temperature 1000, cooling 0.9997",
            "Each variant is run 5 times with different random seeds",
            "Results are best found values, not optimality proofs",
        ],
    ),
    (
        "Benchmark Results",
        [
            "Average / best / standard deviation over 5 runs:",
            "j10_m3_r0_1: avg 2697.0, best 2697, std 0.0",
            "j10_m3_r0_2: avg 6050.0, best 6050, std 0.0",
            "j10_m3_r1_5: avg 3380.0, best 3380, std 0.0",
            "j10_m3_r2_3: avg 4009.0, best 4009, std 0.0",
            "j10_m4_r1_4: avg 14602.0, best 14602, std 0.0",
            "Full data is stored in results_assignment2.csv",
        ],
    ),
    (
        "Conclusions and Lessons Learned",
        [
            "The decoder is the key part of the implementation",
            "Resource constraints cannot be ignored",
            "Simulated Annealing gives feasible best-found solutions",
            "It does not prove optimality",
            "More iterations can improve results, but also increase runtime",
        ],
    ),
    (
        "How to Run",
        [
            "Single instance:",
            "python3 metaheuristic_solver.py --instance instances/PSSAI_PMS_j10_m3_r1_5.json --output results/PSSAI_PMS_j10_m3_r1_5.solution.json --seed 1 --iterations 10000",
            "Experiments:",
            "python3 run_experiments.py --instances \"instances/PSSAI_PMS_j10_*.json\" --runs 5 --iterations 10000",
        ],
    ),
]


def draw_slide(pdf, number, title, bullets):
    width, height = landscape(A4)

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.rect(0, 0, width, height, fill=True, stroke=False)

    pdf.setFillColor(colors.HexColor("#38BDF8"))
    pdf.rect(0, height - 0.35 * cm, width, 0.35 * cm, fill=True, stroke=False)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(1.3 * cm, height - 2.0 * cm, title)

    pdf.setFont("Helvetica", 14)
    y = height - 3.5 * cm
    for bullet in bullets:
        wrapped_lines = wrap_text(bullet, 100)
        pdf.setFillColor(colors.HexColor("#E2E8F0"))
        pdf.drawString(1.6 * cm, y, "- " + wrapped_lines[0])
        y -= 0.62 * cm
        for line in wrapped_lines[1:]:
            pdf.drawString(2.2 * cm, y, line)
            y -= 0.58 * cm
        y -= 0.18 * cm

    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#94A3B8"))
    pdf.drawRightString(width - 1.2 * cm, 0.8 * cm, f"{number} / {len(SLIDES)}")
    pdf.showPage()


def wrap_text(text, max_chars):
    words = text.split()
    lines = []
    current = []

    for word in words:
        candidate = " ".join(current + [word])
        if len(candidate) <= max_chars:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]

    if current:
        lines.append(" ".join(current))

    return lines


def main():
    output_path = Path(__file__).resolve().parent / "assignment2_slides.pdf"
    pdf = canvas.Canvas(str(output_path), pagesize=landscape(A4))
    for index, (title, bullets) in enumerate(SLIDES, start=1):
        draw_slide(pdf, index, title, bullets)
    pdf.save()
    print(f"Slides written to {output_path}")


if __name__ == "__main__":
    main()
