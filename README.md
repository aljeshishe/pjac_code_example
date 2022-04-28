### Description
This is part of PJAC framework. Main purpose of this framework is to test plenty of microservices.
I'm unable to share all sources code of framework due to NDA. 
So I share it's main part which is responsible for creating load in different modes.
1. Local mode(LocalLoadGenerator). 
   1. Finite numbers of tests. 
   2. Process terminates when all tests are done.
2. Stress mode(StressLoadGenerator) 
   1. Local web server is started for management
   2. Infinite number of tests could be started via HTTP request. 
   3. Commands are received via HTTP
   4. Tests run until user terminates stress session.
3. Service mode(ServiceLoadGenerator) 
   1. Local web server is started for management
   1. Single test could be started via HTTP request. 
   4. Tests run until user terminates stress session.
