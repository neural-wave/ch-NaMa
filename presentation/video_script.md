# Video script (2 minutes)

The judges watch the video first, so it has to carry the whole story: the goal, the method, the results and t7.
About 250 words of narration, spoken calmly, fits in 1:55. Visuals are the deck slides (`NAMA_Neuron_Migration.pptx`),
one terminal run and two notebook outputs.

| Time | Visual | Narration |
|---|---|---|
| 0:00 – 0:15 | Slide 1 (title), then slide 2 (the four numbers) | We are team NAMA from USI. NeuralWave Life must move five thousand policies off Neuron, a thirty-year-old system with no source code left. The new system has to give the same numbers, to the cent and to the day. |
| 0:15 – 0:40 | Slide 3 (the loop), then slide 4 (six tools) | So we treated it as detective work. We write the simplest rule, mark the values it gets wrong, and ask generic tools why: a decision tree that says where a rule breaks, a change-point finder that says when, a search over rounding and date conventions. Each answer becomes a few lines of plain Python. No model runs in the submission, so an auditor can follow every cent. |
| 0:40 – 1:00 | Slide 6 (era chart); point at 2007 | The biggest finding: Neuron is two systems. Before August 2007 the COBOL code cut off the cents, counted the age as days divided by 365 and charged fees by the day. Ignore that, and every offer from that era is wrong. |
| 1:00 – 1:25 | Terminal: `python check.py` (sped up, ends on the score table), then slide 7 | Here is the official scorer on the training data: between 99.7 and 100 percent on every task, in about a minute and a half. Every remaining miss is a value someone changed by hand. Our outlier check finds all 38 known corrections, and 17 that nobody had listed. |
| 1:25 – 1:48 | Slide 8 (t7), then the crosstab of notebook 07 | Then the surprise tax task came without any answers. Same loop, different evidence: Neuron's own tax bookings as labels, and the two examples of the task as anchors. Both come out exact to the cent, and every tax Neuron booked gets an amount. |
| 1:48 – 2:00 | Slide 9 (closing, names) | Rules as code, and tools that know nothing about insurance, so they are ready for the next migration. Thank you. |

## Recording

- Present the deck full screen and record with QuickTime (File > New Screen Recording) or PowerPoint's
  Record > Export to Video; record the voice in one take per row and cut them together if needed.
- Terminal shot: `cd starter_kit && python check.py`. Speed the run up 4x in the edit, or start the recording near the
  end of the run; keep the final score table on screen for about 3 seconds.
- Notebook shot: open `notebooks/07_Task_t7_Without_Targets.ipynb` at the crosstab of section 1 (taxes per country);
  scroll slowly, no narration change needed.
- Export as MP4, 1080p, under 2:00. Upload to https://www.swisstransfer.com and keep the link for the submission.
