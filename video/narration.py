SEGMENTS = [
 ("title", [
   "Every summer, outdoor workers collapse from heat, even when every rule is followed.",
   "This is HeatGuard, a personal heat-strain early warning, built for the Future Health Digital Innovation Challenge."]),
 ("problem", [
   "The International Labour Organization expects heat stress to cost two point two percent of global working hours by twenty thirty.",
   "The UAE already bans outdoor work from twelve thirty to three every summer.",
   "But a fixed time window treats everyone the same.",
   "Here are two workers on the same simulated site, in the same weather.",
   "A new arrival on day four reaches thirty-nine point six degrees. A veteran on day two hundred stays under thirty-seven point three.",
   "Heat risk is individual."]),
 ("how", [
   "HeatGuard combines four inputs: the worker's own heart rate from any low-cost wristband, site weather, the task being done, and days on the job.",
   "A Kalman filter fuses a heat-balance model with the heart rate to estimate core temperature every minute, and forecasts thirty minutes ahead.",
   "The output is a simple traffic light. Amber means a short shade break. Red means rest for fifteen minutes, and a human first-aider is told."]),
 ("demo", [
   "Here is a simulated hot August shift at an Abu Dhabi site. Eight workers, six a.m. to six p.m. The grey band is the statutory midday break.",
   "Watch worker two, a rebar fixer on day four. Early on, HeatGuard sees a high-strain pattern and prompts shade and water.",
   "At eight twenty-three it turns red, and her phone gets the alert in Hindi.",
   "The red line shows what happens with no HeatGuard: she crosses thirty-eight point five at eight thirty and climbs to thirty-nine point six.",
   "The green line is the same worker with HeatGuard. Short rests keep her below thirty-eight point four, all day.",
   "Switch to the supervisor view. The site manager sees only a tier and an action. No temperature, no heart rate. The worker owns the data.",
   "By the end of the shift, five of eight workers would have reached the limit without HeatGuard. With it, none did."]),
 ("results", [
   "Across three thousand held-out simulated worker-shifts, thirty-eight percent of workers reach thirty-eight point five degrees under today's practice, and twenty-two percent under a site-wide W-B-G-T cut-off.",
   "With HeatGuard it is four point three percent, while keeping seven productive hours per shift instead of six.",
   "Eighty-two percent of limit crossings were warned ten or more minutes ahead.",
   "These are simulated results. The next step is calibration against human data."]),
 ("close", [
   "HeatGuard is decision support, not diagnosis. Data is consented and worker-owned, aggregates need five workers, and every red alert reaches a human.",
   "Next: a calibration study, then a pilot at an Abu Dhabi site before next summer.",
   "HeatGuard. From signals to solutions."]),
]
