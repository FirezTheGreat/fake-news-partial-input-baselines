| Condition | What the model sees | Accuracy | Mean ± SD, 5 splits | F1 (fake) | Chance |
|---|---|---|---|---|---|
| E1  Full text | Title + body | 98.4% | 98.5% ± 0.2% | 0.983 | 54.8% |
| E2a  First sentence only | Opening line of the body | 99.1% | 99.0% ± 0.1% | 0.990 | 54.8% |
| E2b  Function words only | Grammatical words + punctuation | 96.8% | 96.8% ± 0.2% | 0.964 | 54.8% |
| E2c  Metadata only | Eight numbers, no text | 86.2% | 86.3% ± 0.1% | 0.842 | 54.8% |
| E3  Source markers stripped | Full text minus dateline, 'Reuters', lead | 97.7% | 97.7% ± 0.2% | 0.975 | 54.8% |
| E3b  + page furniture stripped | E3 minus credits, URLs, handles, media tags; plain quotes | 97.3% | 97.3% ± 0.1% | 0.970 | 54.8% |
| E4 control  ISOT headlines | Headline only, same dataset | 94.6% | 94.7% ± 0.4% | 0.939 | 54.8% |
| E4  ISOT → LIAR | Headline-trained, tested on LIAR | 45.5% | n/a (fixed test set) | 0.549 | 55.8% |
