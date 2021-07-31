
import pandas as pd
import numpy as np
import xgboost as xgb

from copy import copy
import datetime
import pickle

filename = "xgb_model.sav"
loaded_model = pickle.load(open(filename, 'rb'))

date_list = [4, 6, 2016] #April 6, 2016

year = int(date_list[2])
month = int(date_list[1])
day = int(date_list[0])

my_date = datetime.date(year, month, day)

class GA : 
    def __init__(self,location) :
        self.location = location
        self.coordinates = location

    def create_guess(self,points):
        """
            Creates a possible path between all points, returning to the original.
            Input: List of point IDs
        """
        guess = copy(points[1:])
        np.random.shuffle(guess)
        guess.append(points[0])
        guess.insert(0,points[0])
        return list(guess)

    def create_generation(self,points, population=100):
        """
        Makes a list of guessed point orders given a list of point IDs.
        Input:
        points: list of point ids
        population: how many guesses to make
        """
        generation = [self.create_guess(points) for _ in range(population)]
        return generation

    def travel_time_between_points(self,point1_id, point2_id, hour, date, passenger_count = 1, 
                               store_and_fwd_flag = 0, pickup_minute = 0):
        """
        Given two points, this calculates travel between them based on a XGBoost predictive model
        """
        model_data = {'passenger_count': passenger_count,
                    'pickup_longitude' : point1_id[1],
                    'pickup_latitude' : point1_id[0],
                    'dropoff_longitude' : point2_id[1],
                    'dropoff_latitude' : point2_id[0],
                    'store_and_fwd_flag' : store_and_fwd_flag,
                    'latitude_difference' : point2_id[0] - point1_id[0],
                    'longitude_difference' : point2_id[1] - point1_id[1],
                    'trip_distance' : 0.621371 * 6371 * (abs(2 * np.arctan2(np.sqrt(np.square(np.sin((abs(point2_id[0] - point1_id[0]) * np.pi / 180) / 2))), 
                                    np.sqrt(1-(np.square(np.sin((abs(point2_id[0] - point1_id[0]) * np.pi / 180) / 2)))))) + \
                                        abs(2 * np.arctan2(np.sqrt(np.square(np.sin((abs(point2_id[1] - point1_id[1]) * np.pi / 180) / 2))), 
                                    np.sqrt(1-(np.square(np.sin((abs(point2_id[1] - point1_id[1]) * np.pi / 180) / 2))))))),
                    'pickup_month' : my_date.month,
                    'pickup_day' : my_date.day,
                    'pickup_weekday' : my_date.weekday(),
                    'pickup_hour': hour,
                    'pickup_minute' : pickup_minute
                    }
        df = pd.DataFrame([model_data], columns=model_data.keys())
        
        pred = np.exp(loaded_model.predict(xgb.DMatrix(df))) - 1
        return pred[0]

    def make_child(self,parent1, parent2):
        """ 
        Take some values from parent 1 and hold them in place, then merge in values
        from parent2, filling in from left to right with cities that aren't already in 
        the child. 
        """
        list_of_ids_for_parent1 = list(np.random.choice(parent1, replace=False, size=len(parent1)//2))
        child = [-99 for _ in parent1]
        
        for ix in range(0, len(list_of_ids_for_parent1)):
            child[ix] = parent1[ix]
        for ix, gene in enumerate(child):
            if gene == -99:
                for gene2 in parent2:
                    if gene2 not in child:
                        child[ix] = gene2
                        break
        child[-1] = child[0]
        return child

    def make_children(self,old_generation, children_per_couple=1):
        """
        Pairs parents together, and makes children for each pair. 
        If there are an odd number of parent possibilities, one 
        will be left out. 
        
        Pairing happens by pairing the first and last entries. 
        Then the second and second from last, and so on.
        """
        mid_point = len(old_generation)//2
        next_generation = [] 
        
        for ix, parent in enumerate(old_generation[:mid_point]):
            for _ in range(children_per_couple):
                next_generation.append(self.make_child(parent, old_generation[-ix-1]))
        return next_generation

    def fitness_score(self,guess):
        """
        Loops through the points in the guesses order and calculates
        how much distance the path would take to complete a loop.
        Lower is better.
        """
        score = 0
        for ix, point_id in enumerate(guess[:-1]):
            score += self.travel_time_between_points(self.coordinates[point_id], self.coordinates[guess[ix+1]], 11, my_date)
        return score

    def check_fitness(self,guesses):
        """
        Goes through every guess and calculates the fitness score. 
        Returns a list of tuples: (guess, fitness_score)
        """
        fitness_indicator = []
        for guess in guesses:
            fitness_indicator.append((guess, self.fitness_score(guess)))
        return fitness_indicator
    
    def get_breeders_from_generation(self,guesses, take_best_N=10, take_random_N=5, verbose=False, mutation_rate=0.1):
        """
        This sets up the breeding group for the next generation. You have
        to be very careful how many breeders you take, otherwise your
        population can explode. These two, plus the "number of children per couple"
        in the make_children function must be tuned to avoid exponential growth or decline!
        """
        # First, get the top guesses from last time
        fit_scores = self.check_fitness(guesses)
        sorted_guesses = sorted(fit_scores, key=lambda x: x[1]) # sorts so lowest is first, which we want
        new_generation = [x[0] for x in sorted_guesses[:take_best_N]]
        best_guess = new_generation[0]
        
        if verbose:
            # If we want to see what the best current guess is!
            print(best_guess)
        
        # Second, get some random ones for genetic diversity
        for _ in range(take_random_N):
            ix = np.random.randint(len(guesses))
            new_generation.append(guesses[ix])
            
        # No mutations here since the order really matters.
        # If we wanted to, we could add a "swapping" mutation,
        # but in practice it doesn't seem to be necessary
        
        np.random.shuffle(new_generation)
        return new_generation, best_guess

    def evolve_to_solve(self,current_generation, max_generations, take_best_N, take_random_N,
                        mutation_rate, children_per_couple, print_every_n_generations, verbose=False):
        """
        Takes in a generation of guesses then evolves them over time using our breeding rules.
        Continue this for "max_generations" times.
        Inputs:
        current_generation: The first generation of guesses
        max_generations: how many generations to complete
        take_best_N: how many of the top performers get selected to breed
        take_random_N: how many random guesses get brought in to keep genetic diversity
        mutation_rate: How often to mutate (currently unused)
        children_per_couple: how many children per breeding pair
        print_every_n_geneartions: how often to print in verbose mode
        verbose: Show printouts of progress
        Returns:
        fitness_tracking: a list of the fitness score at each generations
        best_guess: the best_guess at the end of evolution
        """
        fitness_tracking = []
        for i in range(max_generations):
            if verbose and not i % print_every_n_generations and i > 0:
                print("Generation %i: "%i, end='')
                print(len(current_generation))
                print("Current Best Score: ", fitness_tracking[-1])
                is_verbose = True
            else:
                is_verbose = False
            breeders, best_guess = self.get_breeders_from_generation(current_generation, 
                                                                take_best_N=take_best_N, take_random_N=take_random_N, 
                                                                verbose=is_verbose, mutation_rate=mutation_rate)
            fitness_tracking.append(self.fitness_score(best_guess))
            current_generation = self.make_children(breeders, children_per_couple=children_per_couple)
        
        return fitness_tracking, best_guess

    def GetFastestRoad(self) :

        current_generation = self.create_generation(list(self.location.keys()),population=500)
        fitness_tracking, best_guess = self.evolve_to_solve(current_generation, 5, 150, 70, 0.5, 3, 5, verbose=True)
        print(fitness_tracking)
        print(best_guess)
        return best_guess
    
    
        

if __name__ == "__main__" : 
    GAObject = GA({'L1': (40.819688, -73.915091),
                  'L2': (40.815421, -73.941761),
                  'L3': (40.764198, -73.910785),
                  'L4': (40.768790, -73.953285),
                  'L5': (40.734851, -73.952950),
                  'L6': (40.743613, -73.977998),
                  'L7': (40.745313, -73.993793),
                  'L8': (40.662713, -73.946101),
                  'L9': (40.703761, -73.886496),
                  'L10': (40.713620, -73.943076),
                  'L11': (40.725212, -73.809179)
             })
    GAObject.GetFastestRoad()