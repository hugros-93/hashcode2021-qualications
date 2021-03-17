# Reference: https://www.kaggle.com/batzner/simulation-and-grading-in-python


import os
from collections import deque, namedtuple

# We use namedtuple for representing streets, schedules and intersections.
# For intersections, we need to update some attributes during the simulation,
# which namedtuple does not allow. For this, it would be best to use
# the recordclass package instead, but it is not available in the Kaggle
# Python docker image. Therefore, we use this class to allow modifying a
# wrapped value without changing the attribute in the namedtuple.

class MutableValue:
    def __init__(self, val=None):
        self.val = val

Street = namedtuple('Street', [
    'id',  # The index of the street
    'start',  # The Intersection object at the start of the street
    'end',  # The Intersection object at the end of the street
    'name',  # A str
    'duration',  # The length of the street in seconds
    'driving_cars',  # A dict mapping car ids (int) to remaining seconds
    'waiting_cars',  # A deque of car ids (int)
    'arrival_times',  # A dict mapping car ids (int) to their arrival times
    'departure_times'  # A dict mapping car ids (int) to their departure times
    # You can compute the seconds that a car was waiting at the end of the street
    # by subtracting the arrival time from the departure time.
])

Intersection = namedtuple('Intersection', [
    'id',  # The index of the intersection
    'incomings',  # A deque of incoming Street objects
    'outgoings',  # A deque of outgoing Street objects
    # The Street object that currently has a green light.
    # Will be wrapped in a MutableValue with a "val" attribute to allow
    # mutating the value without mutating the namedtuple.
    'green_street',
    # An int representing the total number of waiting cars across all
    # incoming streets of this intersection.
    # Will be wrapped in a MutableValue with a "val" attribute to allow
    # mutating the value without mutating the namedtuple.
    'num_waiting_cars',
    # The sum of green times of all incoming streets in the schedule.
    # Will be wrapped in a MutableValue with a "val" attribute to allow
    # mutating the value without mutating the namedtuple.
    'schedule_duration',
    # A list mapping (t mod schedule_duration.val) to the street object
    # that is green at time t.
    'green_street_per_t_mod',
    # A bool indicating whether the green_street ever needs to be
    # updated during the simulation (i.e., whether the schedule has
    # more than one street).
    # Will be wrapped in a MutableValue with a "val" attribute to allow
    # mutating the value without mutating the namedtuple.
    'needs_updates'
])

# We only use street indices and intersection indices here to allow
# fast deep-copies of a schedule for testing out and reverting modifications.
Schedule = namedtuple('Schedule', [
    'i_intersection',  # The index of the intersection
    'order',  # A list of street ids
    'green_times'  # A dict mapping street ids to green times (seconds)
])

def read_input(input_file_path):
    with open(input_file_path) as f:
        lines = deque(f.readlines())
        
    # Parse the first line
    total_duration, num_intersections, num_streets, \
    num_cars, bonus_points = map(int, lines.popleft().split())

    # Create empty intersections
    intersections = tuple(Intersection(id=i,
                                       incomings=deque(),
                                       outgoings=deque(),
                                       green_street=MutableValue(),
                                       num_waiting_cars=MutableValue(0),
                                       green_street_per_t_mod=[],
                                       schedule_duration=MutableValue(),
                                       needs_updates=MutableValue(False))
                          for i in range(num_intersections))

    # Parse the streets
    streets = []
    name_to_street = {}
    for i_street in range(num_streets):
        line = lines.popleft().split()
        start, end = map(int, line[:2])
        name = line[2]
        duration = int(line[3])
        street = Street(id=i_street,
                        start=intersections[start],
                        end=intersections[end],
                        name=name,
                        duration=duration,
                        driving_cars={},
                        waiting_cars=deque(),
                        arrival_times={},
                        departure_times={})
        name_to_street[name] = street
        intersections[start].outgoings.append(street)
        intersections[end].incomings.append(street)
        streets.append(street)

    # Parse the paths
    paths = []
    for _ in range(num_cars):
        line = lines.popleft().split()
        path_length = int(line[0])
        path = line[1:]
        assert len(path) == path_length
        path = deque(name_to_street[name] for name in path)
        paths.append(path)

    return total_duration, bonus_points, intersections, \
           streets, name_to_street, paths

def read_answer(output_file_path, name_to_street):
    with open(output_file_path) as f:
        lines = deque(f.readlines())
    num_schedules = int(lines.popleft())
    schedules = []
    for _ in range(num_schedules):
        i_intersection = int(lines.popleft())
        num_incomings = int(lines.popleft())
        order = []
        green_times = {}
        for _ in range(num_incomings):
            street_name, green_time = lines.popleft().split()
            green_time = int(green_time)
            street = name_to_street[street_name]
            order.append(street.id)
            green_times[street.id] = green_time

        schedule = Schedule(i_intersection=i_intersection,
                            order=order,
                            green_times=green_times)
        schedules.append(schedule)
    return schedules

def reinit(streets, intersections):
    # Reinitialize mutable data structures
    for street in streets:
        street.driving_cars.clear()
        street.waiting_cars.clear()
        street.arrival_times.clear()
        street.departure_times.clear()

    for intersection in intersections:
        intersection.green_street.val = None
        intersection.num_waiting_cars.val = 0
        intersection.green_street_per_t_mod.clear()
        intersection.schedule_duration.val = None
        intersection.needs_updates.val = False

def grade(schedules, streets, intersections, paths, total_duration, bonus_points):
    reinit(streets, intersections)
    
    # We will consume the deques in the paths list. Save a copy of them
    # for later to reset the paths after the simulation.
    paths_copy = [path.copy() for path in paths]

    # Iterate through the schedules and initialize the intersections.
    intersection_ids_with_schedules = set()
    for schedule in schedules:
        intersection = intersections[schedule.i_intersection]
        intersection_ids_with_schedules.add(intersection.id)
        first_street = streets[schedule.order[0]]
        intersection.green_street.val = first_street
        intersection.needs_updates.val = len(schedule.order) > 1
        schedule_duration = 0
        green_street_per_t_mod = intersection.green_street_per_t_mod
        for street_id in schedule.order:
            green_time = schedule.green_times[street_id]
            for _ in range(green_time):
                green_street_per_t_mod.append(streets[street_id])
            schedule_duration += green_time
        intersection.schedule_duration.val = schedule_duration

    # intersection_ids_with_waiting_cars is restricted to intersections 
    # with schedules
    intersection_ids_with_waiting_cars = set()
    for i_car, path in enumerate(paths):
        street = path.popleft()
        street.waiting_cars.append(i_car)
        if street.end.id in intersection_ids_with_schedules:
            intersection_ids_with_waiting_cars.add(street.end.id)
        street.end.num_waiting_cars.val += 1

    street_ids_with_driving_cars = set()
    score = 0
    
    # Main simulation loop
    for t in range(total_duration):
        
        # Drive across intersections
        # Store the ids of intersections that don't have waiting cars after this.
        intersection_ids_to_remove = set()
        for i_intersection in intersection_ids_with_waiting_cars:
            intersection = intersections[i_intersection]

            if intersection.needs_updates.val:
                # Update the green street
                t_mod = t % intersection.schedule_duration.val
                intersection.green_street.val = intersection.green_street_per_t_mod[t_mod]

            green_street = intersection.green_street.val
            waiting_cars = green_street.waiting_cars
            if len(waiting_cars) > 0:
                # Drive across the intersection
                waiting_car = waiting_cars.popleft()
                green_street.departure_times[waiting_car] = t
                next_street = paths[waiting_car].popleft()
                next_street.driving_cars[waiting_car] = next_street.duration
                street_ids_with_driving_cars.add(next_street.id)

                intersection.num_waiting_cars.val -= 1
                if intersection.num_waiting_cars.val == 0:
                    intersection_ids_to_remove.add(i_intersection)

        intersection_ids_with_waiting_cars.difference_update(intersection_ids_to_remove)

        # Drive across roads
        # Store the ids of streets that don't have driving cars after this.
        street_ids_to_remove = set()
        for i_street in street_ids_with_driving_cars:
            street = streets[i_street]
            driving_cars = street.driving_cars
            for car in list(driving_cars):
                # Update the "time to live" of this car, i.e. the remaining
                # driving seconds.
                ttl = driving_cars[car]
                ttl -= 1
                if ttl < 0:
                    raise ValueError
                elif ttl == 0:
                    # Reached the end of the street
                    del driving_cars[car]
                    if len(paths[car]) == 0:
                        # FINISH
                        score += bonus_points
                        score += total_duration - t - 1
                    else:
                        street.waiting_cars.append(car)
                        street.end.num_waiting_cars.val += 1
                        street.arrival_times[car] = t + 1
                        intersection_id = street.end.id
                        if intersection_id in intersection_ids_with_schedules:
                            intersection_ids_with_waiting_cars.add(intersection_id)
                else:
                    # The car is still driving on the street
                    driving_cars[car] = ttl
            if len(driving_cars) == 0:
                street_ids_to_remove.add(i_street)
        street_ids_with_driving_cars.difference_update(street_ids_to_remove)

    # We are done with the simulation. Restore the paths.
    for i_path in range(len(paths)):
        paths[i_path] = paths_copy[i_path]
    return score

def get_score(INPUT_FILE_PATH, OUTPUT_FILE_PATH):

    total_duration, bonus_points, intersections, \
    streets, name_to_i_street, paths = read_input(INPUT_FILE_PATH)

    schedules = read_answer(OUTPUT_FILE_PATH, name_to_i_street)

    score = grade(schedules, streets, intersections, paths, total_duration, bonus_points)

    return score