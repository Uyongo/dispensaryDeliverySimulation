import simpy
import numpy
import pandas
import random
import statistics
import pdb

############################################################################
### Object for each simulation run                                       ###
############################################################################
class Dispensary(object):
  def __init__(self, env, parametersByUser):
    self.env = env
    self.parametersByUser = parametersByUser
    self.averageStepDur = self.parametersByUser['averageStepDur'] #float
    self.interarrivTime = self.parametersByUser['interarrivTime'] #float
    self.prescriptionCounter = 1
    self.weekdayPickup = self.parametersByUser['weekdayPickup'] #list of numbers (times)
    self.weekendPickup = self.parametersByUser['weekendPickup'] #list of numbers (times)
    self.Pharmacists = simpy.Resource(env, parametersByUser['numPharmacists'])
    self.Labellers = simpy.Resource(env, parametersByUser['numLabellers'])
    self.Dispensers = simpy.Resource(env, parametersByUser['numDispensers'])
    self.FinalCheckers = simpy.Resource(env, parametersByUser['numFinCheckers'])
    self.averageTranspDur = self.parametersByUser['averageTranspDur']
    self.standDevOfTranspDur = self.parametersByUser['standDevOfTranspDur']
    self.namesOfWeekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', \
                            'Friday', 'Saturday', 'Sunday']
    self.openingHoursWeekdays = [9, 17.5]
    self.openingHoursWeekends = [9, 13]
    self.openingHours = self.openingHoursDict(self.openingHoursWeekdays, 
                                              self.openingHoursWeekends, 
                                              self.namesOfWeekdays)
    self.transportTimes = self.endlessTransportTimes(self.weekdayPickup,
                                                      self.weekendPickup)
    self.shiftTimes = self.endlessShiftTimes(self.openingHoursWeekdays,
                                              self.openingHoursWeekends)
    self.monitoringDf = pandas.DataFrame(index = [1],
                                     columns = ['averageStepDur',
                                                'interarrivTime',
                                                'arrivalTime',
                                                'timeOfDayOfArrival',
                                                'dayOfWeekOfArrival',
                                                'verifStarted',
                                                'verifFinished',
                                                'labelStarted',
                                                'labelFinished',
                                                'dispStarted',
                                                'dispFinished',
                                                'finCheckStarted',
                                                'finCheckFinished',
                                                'putInStore',
                                                'timeOfDayOfPutInStore',
                                                'dayOfWeekOfPutInStore',
                                                'timeOfPickup',
                                                'timeOfDelivery'])
    self.pickupData = pandas.DataFrame(columns = ['timeBeforePickup',
                                                  'itemsInStoreBefore',
                                                  'timeAfterPickup',
                                                  'itemsInStoreAfter'])
    self.resultsDict = self.parametersByUser
  
  #This function merely creates a dictionary of opening hours for convenience:
  def openingHoursDict(self, openingHoursWeekdays, openingHoursWeekends,
    namesOfWeekdays):
      openingDict = {}
      for day in namesOfWeekdays[:5]:
          openingDict.update({day: openingHoursWeekdays})
      for day in namesOfWeekdays[5:]:
          openingDict.update({day: openingHoursWeekends})
      return openingDict
  
  #A generator function that yields an endless sequence of weekday names in
  #order, allowing for starting at a chosen day of the week:
  def endlessWeekdayGen(self, startIndex):
      n = len(self.namesOfWeekdays)
      i = 0
      while True:
          yield self.namesOfWeekdays[(i + startIndex) % n]
          i += 1
          
  #Establishing the time of day against the simulation time (which could be
  #a very large number).
  def timeOfDayEstablisher(self, simulationTime):
      timeOfDay = simulationTime % 24
      return timeOfDay
    
  #This simulation assumes that one unit of simulation time corresponds to
  #one hour of real time. The function below returns the name of the week
  #(as defined before) against the simulation Time.
  def hoursToWeekdayConverter(self, simulationTime):
      #calculating time in the current week (a week has 168 hours)
      timeInWeek = simulationTime % 168
      #determining the day of the week, assuming the simulation starts
      #on a Monday
      dayInWeek = int(timeInWeek / 24)
      return self.namesOfWeekdays[dayInWeek]
    
  #Generating an endless sequence of times when dispensary shifts start
  #and stop, respectively:
  def endlessShiftTimes(self, 
                        openingHoursWeekdays,
                        openingHoursWeekends):
      hoursPassed = 0
      while True:
          for day in range(1, 6):
              for alt in range(2):
                  nextTime = hoursPassed + openingHoursWeekdays[alt] 
                  yield nextTime
              hoursPassed += 24
          for day in range(6, 8):
              for alt in range(2):
                  nextTime = hoursPassed + openingHoursWeekends[alt]
                  yield nextTime
              hoursPassed += 24
              
  #Generating an endless sequence of delivery times from
  #the dispensary to units in simulation time:
  def endlessTransportTimes(self, 
                            transportWeekdays,
                            transportWeekends):
      hoursPassed = 0
      while True:
          for day in range(1, 6):
              for t in transportWeekdays:
                  nextTime = hoursPassed + t 
                  yield nextTime
              hoursPassed += 24
          for day in range(6, 8):
              for t in transportWeekends:
                  nextTime = hoursPassed + t
                  yield nextTime
              hoursPassed += 24   
  
  #The delay due to an activity, started at a given time-point during a shift,
  #might need to be adjusted, given time-periods when staff are active and
  #inactive, respectively. This function takes a period, as calculated or
  #estimated by the simulation model, and distributes it over several shifts,
  #if it exceeds the end of the shift in which it started, adding inactivity
  #periods to the overall delay, if necessary.
  def durationAdjuster(self,
                        timeToProcessPrescription,
                        timeOfDay,
                        dayOfWeek):
      overallDelay = timeToProcessPrescription
      timeOfProcessStillLeft = timeToProcessPrescription
      openingTimes = self.openingHours[dayOfWeek]
  
      #initialising the generator iterator object producing one weekday
      #name after the other:
      nextDay = self.endlessWeekdayGen((self.namesOfWeekdays.index(dayOfWeek) + 1) \
                                          % len(self.namesOfWeekdays))    
      
      #checking if the duration of the processing extends beyond the closing
      #time of the dispensary:
      while (timeOfDay + timeOfProcessStillLeft) > max(openingTimes):
          timeOfProcessStillLeft = timeOfProcessStillLeft - \
                                   (max(openingTimes) - timeOfDay)
          #capturing the next day's name:
          D = next(nextDay)
          timeOfDay = min(self.openingHours[D])
          overallDelay += (24 - max(openingTimes)) + \
                          timeOfDay
          openingTimes = self.openingHours[D]
      return overallDelay
  
  #def resultsSummariser(self):
   #resultsDict = self.resultsDict
    
    
    
    
############################################################################
###  Global functions below                                              ###
############################################################################

#This process describes the simplified workflow after a prescription (or
#transcription) has been added to the dedicated IT system until its dispensed
#medication(s) are deposited in the dispensary for collection by a driver.
def prescriptionProcessor(env, store, disp):
    #Capturing parameters that are changing per simulation run:
    disp.monitoringDf.loc[disp.prescriptionCounter, 'averageStepDur'] =\
                                               disp.averageStepDur
    disp.monitoringDf.loc[disp.prescriptionCounter, 'interarrivTime'] =\
                                               disp.interarrivTime
    #Capturing arrival time of the prescription:    
    arrivalTime = env.now
    disp.monitoringDf.loc[disp.prescriptionCounter, 'arrivalTime'] = arrivalTime
    timeOfDay = disp.timeOfDayEstablisher(arrivalTime)
    disp.monitoringDf.loc[disp.prescriptionCounter,
                          'timeOfDayOfArrival'] = timeOfDay
    dayOfWeek = disp.hoursToWeekdayConverter(arrivalTime)
    disp.monitoringDf.loc[disp.prescriptionCounter,
                          'dayOfWeekOfArrival'] = dayOfWeek
    #Four steps are required to process a prescription. Each will take a 
    #certain time as defined (on average) by disp.averageStepDur. Each step 
    #also requires a different staff-group for processing as a resource. Also, 
    #each step's duration might extend beyond the closing time for the day and 
    #require finishing on the next day (or even the day after that) - the 
    #disp.durationAdjuster function is meant to adjust delays accordingly:
    #Step 1:
    with disp.Pharmacists.request() as request:
      yield request
      timeToProcessPrescription = numpy.random.exponential(disp.averageStepDur)                    
      overallDelay = disp.durationAdjuster(timeToProcessPrescription,
                                            timeOfDay,
                                            dayOfWeek)
      #Capturing time when verifying starts:
      verifStarted = env.now
      disp.monitoringDf.loc[disp.prescriptionCounter, 'verifStarted'] = \
                                                                  verifStarted
      yield env.timeout(overallDelay)
    #Capturing time when prescription is verified:
    verifFinished = env.now
    disp.monitoringDf.loc[disp.prescriptionCounter, 'verifFinished'] = \
                                                                verifFinished
    #Step 2:
    with disp.Labellers.request() as request:
      yield request
      timeToProcessPrescription = numpy.random.exponential(disp.averageStepDur)                    
      overallDelay = disp.durationAdjuster(timeToProcessPrescription,
                                            timeOfDay,
                                            dayOfWeek)
      #Capturing time when labelling starts:
      labelStarted = env.now
      disp.monitoringDf.loc[disp.prescriptionCounter, 'labelStarted'] = \
                                                                  labelStarted
      yield env.timeout(overallDelay)
    #Capturing time when prescription is labelled:
    labelFinished = env.now
    disp.monitoringDf.loc[disp.prescriptionCounter, 'labelFinished'] = \
                                                                labelFinished
    #Step 3:
    with disp.Dispensers.request() as request:
      yield request
      timeToProcessPrescription = numpy.random.exponential(disp.averageStepDur)                    
      overallDelay = disp.durationAdjuster(timeToProcessPrescription,
                                            timeOfDay,
                                            dayOfWeek)
      #Capturing time when dispensing starts:
      dispStarted = env.now
      disp.monitoringDf.loc[disp.prescriptionCounter, 'dispStarted'] = \
                                                                  dispStarted
      yield env.timeout(overallDelay)
    #Capturing time when prescription is dispensed:
    dispFinished = env.now
    disp.monitoringDf.loc[disp.prescriptionCounter, 'dispFinished'] = \
                                                                dispFinished
    #Step 4:
    with disp.FinalCheckers.request() as request:
      yield request
      timeToProcessPrescription = numpy.random.exponential(disp.averageStepDur)                    
      overallDelay = disp.durationAdjuster(timeToProcessPrescription,
                                            timeOfDay,
                                            dayOfWeek)
      #Capturing time when final checking starts:
      finCheckStarted = env.now
      disp.monitoringDf.loc[disp.prescriptionCounter, 'finCheckStarted'] = \
                                                              finCheckStarted
      yield env.timeout(overallDelay)
    #Capturing time when prescription is final checked:
    finCheckFinished = env.now
    disp.monitoringDf.loc[disp.prescriptionCounter, 'finCheckFinished'] = \
                                                              finCheckFinished
    #Putting dispensed items into a store before transport:
    yield store.put(f'{disp.prescriptionCounter}')
    #Capturing when dispensed items are put into the store. This should be the 
    #same as finCheckFinished (unless there is an error). 
    putInStore = env.now
    disp.monitoringDf.loc[disp.prescriptionCounter,
                          'putInStore'] = putInStore
    timeOfDayOfPutInStore = disp.timeOfDayEstablisher(putInStore)
    disp.monitoringDf.loc[disp.prescriptionCounter,
                          'timeOfDayOfPutInStore'] = timeOfDayOfPutInStore
    dayOfWeekOfPutInStore = disp.hoursToWeekdayConverter(putInStore)
    disp.monitoringDf.loc[disp.prescriptionCounter,
                          'dayOfWeekOfPutInStore'] = dayOfWeekOfPutInStore
    
##Transporting dispensed items to wards/units at defined times
##during the day:
def pickupFromDispensary(env, store, disp):
    while True:
        prescriptionsPerRun = []
        #Ensuring that transport only occurs at times defined in the
        #transportTimes generator iterator:
        yield env.timeout(next(disp.transportTimes)\
                          - env.now)
        i = len(disp.pickupData)
        #Documenting data on each pick-up time:
        disp.pickupData.loc[i, 'timeBeforePickup'] = env.now
        disp.pickupData.loc[i, 'itemsInStoreBefore'] = len(store.items)
        #Each item in store at a given time gets removed from the store:
        while len(store.items) > 0:
            prescriptionNo = yield store.get()
            prescriptionCounter = int(prescriptionNo)
            prescriptionsPerRun.append(prescriptionCounter)
            disp.monitoringDf.loc[prescriptionCounter,
                                  'timeOfPickup'] = env.now
        #The next two entries to the dataframe are just to monitor that the
        #store gets emptied at each pick-up:
        disp.pickupData.loc[i, 'timeAfterPickup'] = env.now
        disp.pickupData.loc[i, 'itemsInStoreAfter'] = len(store.items)
        #Prompting the delivery of picked up prescriptions to the units:
        yield env.process(transportToUnits(env,prescriptionsPerRun, disp))

def transportToUnits(env, prescriptionsPerRun, disp):
    #A normal distribution of delivery times is assumed:
    yield env.timeout(numpy.random.normal(disp.averageTranspDur, 
                                          disp.standDevOfTranspDur))
    #Documentation of each received prescription in the monitoring dataframe:
    timeOfDelivery = env.now
    for p in prescriptionsPerRun:
        disp.monitoringDf.loc[p, 'timeOfDelivery'] = timeOfDelivery

#Generating prescription items when dispensary is open, i.e.
#depending on the opening times on weekdays and weekends. The
#average processing time for prescriptions and the mean
#interarrival time are also taken from the disp object.
def prescriptionGenerator(env, store, disp):
    while True:
        yield env.timeout(next(disp.shiftTimes) - env.now)
        nextTime = next(disp.shiftTimes)
        while env.now <= nextTime:
            env.process(prescriptionProcessor(env, store, disp))  
            yield env.timeout(numpy.random.exponential(disp.interarrivTime))
            disp.prescriptionCounter += 1
    
def simulationRunner(parametersByUser): 
    env = simpy.Environment()
    store = simpy.Store(env, capacity=1000000)
    disp = Dispensary(env, parametersByUser)
    
    env.process(prescriptionGenerator(env, store, disp))
                                      
    for inst in range(6):
        inst = env.process(pickupFromDispensary(env, store, disp))
        
    env.run(until = 168) #168 hours are one week.
    
    ##Analysing monitoring data-frame by adding calculated fields:
    disp.monitoringDf['waitingForVerif'] = disp.monitoringDf['verifStarted'] \
                                      - disp.monitoringDf['arrivalTime']
    disp.monitoringDf['waitingForLabel'] = disp.monitoringDf['labelStarted'] \
                                      - disp.monitoringDf['verifFinished']
    disp.monitoringDf['waitingForDisp'] = disp.monitoringDf['dispStarted'] \
                                      - disp.monitoringDf['labelFinished']
    disp.monitoringDf['waitingForFinCheck'] = disp.monitoringDf['finCheckStarted'] \
                                      - disp.monitoringDf['dispFinished']
    disp.monitoringDf['waitingForTransp'] = disp.monitoringDf['timeOfPickup'] \
                                      - disp.monitoringDf['putInStore']                                  
    disp.monitoringDf['overallWaiting'] = disp.monitoringDf['waitingForVerif']\
                                        + disp.monitoringDf['waitingForLabel']\
                                        + disp.monitoringDf['waitingForDisp']\
                                        + disp.monitoringDf['waitingForFinCheck']\
                                        + disp.monitoringDf['waitingForTransp']
    disp.monitoringDf['processInDisp'] = disp.monitoringDf['putInStore'] \
                                      - disp.monitoringDf['arrivalTime']
    disp.monitoringDf['throughputTime'] = disp.monitoringDf['timeOfDelivery'] \
                                      - disp.monitoringDf['arrivalTime']
    #Calculating and outputting results (it appears the 'mean' function 
    #automatically ignores None values):
    meanThroughput = round(disp.monitoringDf['throughputTime'].mean(), 2)
    meanWaiting = round(disp.monitoringDf['overallWaiting'].mean(), 2)
    totalWorkItems = len(disp.monitoringDf)
    notCompletedWorkItems = disp.monitoringDf['timeOfDelivery'].isnull().sum()
    completedWorkItems = totalWorkItems - notCompletedWorkItems
    percentageCompleted = round((completedWorkItems / totalWorkItems) * 100, 2)
    
    results = disp.resultsDict.update({'meanThroughput': meanThroughput,
                                      'meanWaiting': meanWaiting,
                                      'totalWorkItems': totalWorkItems,
                                      'completedWorkItems': completedWorkItems,
                                      'percentageCompleted': percentageCompleted})
    #Saving raw data to .csv file:
    disp.monitoringDf.to_csv('monitoringDf.csv', index = True)
    #Analysing raw data and adding results to new data-frame:
    return results
    
def getUserInput():
  parameters = {'averageStepDur': 15/60, #0 float
                'interarrivTime': 5/60, #1 float
                'numPharmacists': 3, #2 int
                'numLabellers': 3, #3 int
                'numDispensers': 3, #4 int
                'numFinCheckers': 3, #5 int
                'averageTranspDur': 1, #6 float
                'standDevOfTranspDur': 12/60, #7 float
                'weekdayPickup': [10, 12, 15, 17], #8 list
                'weekendPickup': [12]} #9 list
  labels = list(parameters.keys())
  questions = ['Average duration of each step (default is 15/60): ',
                'Average time between appearance of new prescriptions (default 5/60): ',
                'Number of pharmacists working (default is 3): ',
                'Number of labellers working (default is 3): ', 
                'Number of dispensers working (default is 3): ',
                'Number of final checkers working (default is 3): ',
                'Average duration of transport (default is 1): ',
                'Standard deviation of transport duration (default is 12/60): ',
                "Pickup times during the week (default '10 12 15 17'): ",
                "Pickup times on weekends (default '12'): "]
  
  print('Please provide the following parameters of the simulation run:')
  
  for iteration, param in enumerate(parameters):
    answer = input(questions[iteration])
    if iteration >= (len(parameters) - 2):
      if answer == '':
        continue
      else:
        stringList = answer.split()
        answer = [eval(i) for i in stringList]
        parameters.update({labels[iteration]: answer})
    else:
      while not(str(answer).replace('.', '').isdigit() or str(answer) == ''):
        print('Please try again. You need to enter a positive number or nothing.')
        answer = input(questions[iteration])
      if answer == '':
        continue
      else:
        if iteration in [2, 3, 4, 5]:
          parameters.update({labels[iteration]: int(answer)})
        else:
          parameters.update({labels[iteration]: float(answer)})
      
  return parameters


###########################################################
####   Code for starting of simulation below           ####
###########################################################

random.seed(42)
parametersByUser = getUserInput()

###Setting breakpoint for debugger:
pdb.set_trace()

k = simulationRunner(parametersByUser)
print(k)





