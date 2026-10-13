| Condition | What the model sees | Accuracy | Mean ± SD, 5 splits | F1 (fake) | Chance |
|---|---|---|---|---|---|
| E1  Full text | Title + body | 98.4% | 98.5% ± 0.2% | 0.983 | 54.8% |
| E2a  First sentence only | Opening line of the body | 99.1% | 99.0% ± 0.1% | 0.990 | 54.8% |
| E2b  Function words only | Grammatical words + punctuation | 96.8% | 96.8% ± 0.2% | 0.964 | 54.8% |
| E2c  Metadata only | Eight numbers, no text | 86.2% | 86.3% ± 0.1% | 0.842 | 54.8% |
| E2d  Sentiment only | Eight VADER scores, stripped text | 73.8% | 74.1% ± 0.5% | 0.696 | 54.8% |
| E2e  Named entities only | Entity-type counts, stripped text | 81.1% | 81.6% ± 0.4% | 0.782 | 54.8% |
| E3  Source markers stripped | Full text minus dateline, 'Reuters', lead | 97.7% | 97.7% ± 0.2% | 0.975 | 54.8% |
| E3b  + page furniture stripped | E3 minus credits, URLs, handles, media tags; plain quotes | 97.3% | 97.3% ± 0.1% | 0.970 | 54.8% |
| E3c  Stripped, function words only | E3b text reduced to function words | 90.7% | 90.8% ± 0.1% | 0.895 | 54.8% |
| E4 control  ISOT headlines | Headline only, same dataset | 94.6% | 94.7% ± 0.4% | 0.939 | 54.8% |
| E4  ISOT → LIAR | Headline-trained, tested on LIAR | 45.5% | n/a (fixed test set) | 0.549 | 55.8% |
| E4  ISOT → LIAR, no half-true | LIAR without the ambiguous label | 51.1% | n/a (fixed test set) | 0.631 | 55.6% |
| E4b control  McIntire in-domain | McIntire full text, its own split | 91.9% | 91.2% ± 0.5% | 0.921 | 50.7% |
| E4b  ISOT → McIntire, full text | Full articles, other dataset | 61.2% | n/a (fixed test set) | 0.700 | 50.7% |
| E4b  ISOT → McIntire, stripped | Both sides E3b-stripped | 59.8% | n/a (fixed test set) | 0.687 | 50.7% |
| E4b  ISOT → McIntire, function words | Stripped function words | 63.9% | n/a (fixed test set) | 0.671 | 50.7% |
| E4b  McIntire → ISOT, full text | Reverse direction | 65.0% | n/a (fixed test set) | 0.648 | 54.8% |
| E5a  US politics only: full text | Topic-matched subset | 98.3% | 98.5% ± 0.1% | 0.986 | 60.9% |
| E5b  US politics only: stripped | Topic-matched, E3b text | 96.7% | 97.0% ± 0.2% | 0.973 | 60.9% |
| E5c  US politics only: stripped function words | Topic-matched, no markers, no content words | 90.3% | 90.5% ± 0.2% | 0.920 | 60.9% |
| E5d  US politics only: stripped metadata | Topic-matched, eight numbers | 85.8% | 85.6% ± 0.3% | 0.884 | 60.9% |
| E1  Full text (SVM) | As E1, linear SVM | 99.3% | 99.3% ± 0.1% | 0.992 | 54.8% |
| E2a  First sentence (SVM) | As E2a, linear SVM | 99.7% | 99.6% ± 0.1% | 0.996 | 54.8% |
| E2b  Function words (SVM) | As E2b, linear SVM | 97.5% | 97.4% ± 0.1% | 0.972 | 54.8% |
| E3b  Page furniture stripped (SVM) | As E3b, linear SVM | 98.1% | 98.1% ± 0.1% | 0.979 | 54.8% |
