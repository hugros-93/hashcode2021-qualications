# Imports
import tqdm
import numpy as np

# Class


class Problem():
    def __init__(self, dur, nb_inters, nb_street, nb_cars, score_voiture):
        self.dur = int(dur)
        self.nb_inters = int(nb_inters)
        self.nb_street = int(nb_street)
        self.nb_cars = int(nb_cars)
        self.score_voiture = int(score_voiture)

    def __repr__(self):
        representation = "Problem:"
        representation += "\n dur:\t"+str(self.dur)
        representation += "\n num intersection :\t"+str(self.nb_inters)
        representation += "\n num 2 rues:\t"+str(self.nb_street)
        representation += "\n num voiture:\t"+str(self.nb_cars)
        representation += "\n score par voiture:\t"+str(self.score_voiture)
        return representation


class Street():
    def __init__(self, start, end, name, time):
        self.start = int(start)
        self.end = int(end)
        self.name = str(name)
        self.time = int(time)

    def __repr__(self):
        representation = "Street:"
        representation += "\n start:\t"+str(self.start)
        representation += "\n end:\t"+str(self.end)
        representation += "\n name:\t"+str(self.name)
        representation += "\n time:\t"+str(self.time)
        return representation


class Car():
    def __init__(self, car_id, len_path, path):
        self.car_id = car_id
        self.len_path = int(len_path)
        self.path = path

    def __repr__(self):
        representation = "Car:"
        representation += "\n ID voiture:\t"+str(self.car_id)
        representation += "\n longueur parcours:\t"+str(self.len_path)
        representation += "\n path:\t"+str(self.path)
        return representation

    @classmethod
    def from_line(cls, line, line_id):
        line_data = line.split()
        len_path = int(line_data[0])
        path = line_data[1:]
        return cls(line_id, len_path, path)


class Intersection():
    def __init__(self, id):
        self.id = id
        self.list_street = set()

    def add_street(self, street):
        self.list_street.add(street)

    def __repr__(self):
        representation = "Intersection :"
        representation += "\n id :\t" + str(self.id)
        representation += "\nStreets:\n"
        representation += "###################\n"
        for i, s in enumerate(list(self.list_street)):
            representation += "Street"+str(i) + "\n"
            representation += str(s)
            representation += "\n=====\n"
        representation += "###################\n"
        return representation

# Input parsing


def get_data(input_file):
    ville = []
    trajets = []
    intersections = []

    with open(input_file, "r") as file:

        problem_data = file.readline()
        boulbi = Problem(*problem_data.split())

        # remplit la ville avec les streets
        for _ in range(boulbi.nb_street):
            line_data = file.readline()
            tempo_ville = Street(*line_data.split())
            ville.append(tempo_ville)

        # remplit trajet avec les voitures
        for i, _ in enumerate(range(boulbi.nb_cars)):
            line_data = file.readline()
            tempo_trajet = Car.from_line(line_data, i)
            trajets.append(tempo_trajet)

    # Creation des intersections
    for i in range(boulbi.nb_inters):
        tempo_intersection = Intersection(i)
        intersections.append(tempo_intersection)

    # remplissage des intersections
    for street in ville:
        intersections[street.end].add_street(street)

    return ville, trajets, intersections

def heuristic_2_mort(ville, trajets, intersections, delay):

    solution = []
    passage_dict = build_passage_dict(trajets)
    sorted_keys_passage_dict = sorted(
        passage_dict, 
        key=passage_dict.get, 
        reverse=True
    )

    for intersec_solution in tqdm.tqdm(intersections):
        inter_to_check = [key for key in sorted_keys_passage_dict \
            if key in [x.name for x in intersec_solution.list_street]]
        if len(inter_to_check) > 0:
            values_inter_to_check = [passage_dict[street]
                                     for street in inter_to_check]
            values_inter_to_check = rescale(values_inter_to_check, delay)
            sol_inter = [intersec_solution.id, len(inter_to_check), []]
            # prepare export
            for i, street in enumerate(inter_to_check):
                sol_inter[2].append([street, values_inter_to_check[i]])
            solution.append(sol_inter)
    return solution

def get_new_solution(solution, n=10):
    for _ in range(n):
        i = random.randint(0, len(solution)-1)
        random.shuffle(solution[i][2])
    return solution

def get_new_solution_tuning(solution, n=10):
    for i in tqdm.tqdm(range(len(solution))):
        list_solutions = [solution for _ in range(n)]
        list_score = []
        for j in range(n):
            random.shuffle(list_solutions[j][i][2])
            
            format_results(format_output(list_solutions[j]), 
                           f"outputs/heuristic_2_rue_{data}_{j}_actual.txt.out", 
                           len(list_solutions[j]))
            list_score.append(get_score(input_file, f"outputs/heuristic_2_rue_{data}_{j}_actual.txt.out"))
            
        solution = list_solutions[np.argmax(list_score)]   
    return solution


# Output
def format_results(solution, output_file, num_sol):

    string_to_write = str(num_sol)+"\n" + solution
    with open(output_file, 'w') as file:
        file.write(string_to_write)

def format_output(solution):
    output = ""
    for inter in solution:
        output_inter = str(inter[0]) + "\n"
        output_inter += str(inter[1])
        for street in inter[2]:
            output_inter += '\n' + street[0] + " " + str(street[1])
        output+=output_inter+'\n'
    return output
    
# Heuristic
def build_passage_dict(list_cars):
    passage_dict = {}
    for gova in list_cars:
        for street in gova.path:
            if street in passage_dict:
                passage_dict[street] += 1
            else:
                passage_dict[street] = 1
    return passage_dict

def rescale(list_values, new_max):
    max_value = np.max(list_values)
    min_value = np.min(list_values)
    if min_value == max_value:
        return [new_max for x in list_values]
    else:
        rescaled_values = list_values / max_value
        return [1 + int((new_max-1) * x) for x in rescaled_values]


def heuristic_2_rue(ville, trajets, intersections, delay):

    solution = ""
    passage_dict = build_passage_dict(trajets)
    sorted_keys_passage_dict = sorted(
        passage_dict, key=passage_dict.get, reverse=False)

    num_sol = 0
    for intersec_solution in tqdm.tqdm(intersections):
        inter_to_check = [key for key in sorted_keys_passage_dict \
            if key in [x.name for x in intersec_solution.list_street]]
        if len(inter_to_check) > 0:
            values_inter_to_check = [passage_dict[street]
                                     for street in inter_to_check]
            values_inter_to_check = rescale(values_inter_to_check, delay)
            sol_inter = str(intersec_solution.id) + "\n"
            num_sol += 1
            sol_inter += str(len(inter_to_check))

            # prepare export
            for i, street in enumerate(inter_to_check):
                sol_inter += '\n' + street + " " + \
                    str(values_inter_to_check[i])
            solution += sol_inter+'\n'

    return solution, num_sol

################################################################

if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", type=str)
    parser.add_argument("--delay", type=int, default=1)
    args = parser.parse_args()

    # Input
    ville, trajets, intersections = get_data(args.input_file)
    
    # Heuristic
    solution_2_rue, num_sol = heuristic_2_rue(
        ville, trajets, intersections, args.delay)
    
    # Output
    output_file = './outputs/heuristic_2_rue_'+args.input_file.split('/')[-1]+'.out'
    format_results(solution_2_rue, output_file, num_sol)
