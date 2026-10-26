# Form answers (copy and paste)

**Challenges:** [Population Health] Climate-Resilient Worker Health

**Solution summary** (1339/2000)
HeatGuard is a personal heat-strain early warning for outdoor workers. Weather alerts and fixed midday breaks treat every worker the same, but heat risk is individual: a worker on day four of the job in a humid morning is at far higher risk than a veteran doing light work. HeatGuard combines four inputs: the worker's own heart rate from any low-cost wristband, site weather, the task class and days on the job. An extended Kalman filter fuses a heat-balance model (metabolism, sweat, evaporation, hydration, acclimatization) with the heart rate to estimate core temperature every minute and forecast it 30 minutes ahead. The result is a traffic light. Amber triggers a 5-minute shade and water break. Red triggers a 15-minute rest and notifies a human first-aider. Alerts reach the worker in Hindi, Urdu, Bengali, Malayalam, Nepali, Tagalog or English by WhatsApp or SMS. Privacy is built in: the worker owns the data, the supervisor sees only the tier and action, and authorities see aggregates of at least 5 workers. In a held-out simulated cohort of 3,000 worker-shifts, 37.8% of workers reach a core temperature of 38.5 C under status quo and 22.4% under a site-wide WBGT cut-off, versus 4.3% with HeatGuard, which keeps 7.0 productive hours per shift (cut-off: 6.0). Results are synthetic; a calibration study and pilot are planned.

**Solution stage:** Prototype

**What has been built during the challenge?** (851/1500)
Built during the challenge by one person: (1) a physics-based synthetic worker and weather simulator with individual variation, sensor dropouts and outliers; (2) the HeatGuard estimator, an extended Kalman filter with 30-minute forecasting and uncertainty; (3) three work-rest policies (status quo, site WBGT cut-off, HeatGuard) evaluated in closed loop; (4) validation on 6,000 held-out synthetic worker-shifts with fairness splits, ablations and bootstrap confidence intervals; (5) multilingual alert layer, role-based privacy views and a FastAPI service; (6) 7 automated tests; (7) a live site console replaying a simulated hot August shift; (8) a 3-minute demo video and the submission deck. Key measured results: estimate error 0.43 C RMSE; 82% of 38.5 C events warned 10+ minutes ahead (median 63 min). All results are simulated, not human data.

**Technology type:** Machine learning, Software application, Analytics

**Prototype / demo link:** https://abdulmannaan502.github.io/heatguard/   (code: https://github.com/abdulmannaan502/heatguard)

**Upload your solution deck:** HeatGuard_Submission.pdf

**Is your solution software-based, hardware-based, or both?** Software

**Share a link to a short demo video:** (paste the YouTube link after upload; set visibility to Unlisted or Public)
