 # A simple simulation model including four consecutive steps, storage of finished workitems and delivery at defined times

This simple simulation model aims to explore how (mean) throughput times, waiting times and other relevant performance metrics are affected by changes to the number of available resources and delivery times. Work-items (referred to as 'prescriptions' in the code, yet this could also be applicable to many other work-items), arrive at the beginning of the of the process (see map further below) at exponentially distributed interarrival times (generated by the _prescriptionGenerator_ function). Each of the four consecutive work-steps has associated and dedicated (and unique) resources. The durations of these steps are exponentially distributed. These are referred to as Pharmacists, Labellers, Dispensers, and FinalCheckers in the code (these names could be substituted with other names and only serve to distinguish them clearly in the code). Other relevant properties of the simulation model are defined as attributes in the _Dispensary_ class; these include opening times of the dispensary (dispensary is the name of the arena where the process is progressed; the four steps and deliveries are only progressed at defined periods of the day), average durations of the four steps, average transport durations, and others. The attributes of _Dispensary_ also include data-frames for monitoring of the progress of each work-item (i.e. prescription) and the creation of aggregate results (including throughput times and waiting times).

The main question this simulation model aims to answer is how throughput times are affected by a reduction in available delivery times and how this effect can, in turn, be impacted on by the availability (or lack) of resources (referred to as Pharmacists, Labellers, Dispensers, and FinalCheckers in the code). The underlying assumption is that (mean) throughput times will be disproportionately affected by reducing delivery times (i.e. by more than just by a proportion of the number of delivery times per day corresponding to the reduction) in situations where resources are scarce (i.e. where queues build up readily and contribute to a significant, if not the largest, part of (mean) throughput times). This situation of scarce resources arguably applies to many industries, and in particular to the healthcare industry. 


![image](https://github.com/Uyongo/dispensaryDeliverySimulation/assets/53852545/dbff4a7c-8450-4558-bb7a-c206bf08415d)
