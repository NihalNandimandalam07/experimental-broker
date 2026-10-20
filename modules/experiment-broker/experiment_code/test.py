import yaml
import json
import sys
import os
sys.path.append('vr_runner_lite')
#sys.path.append('../activities')
import experiment as exp
#from experiment import run_experiment

read_file_path = 'tests/example_experiments\Demo-Kubernetes(EKS)-Worker Node (Pod)-State-TerminationCrash.yml'
write_file_path = 'tests/journals/experiment_journals2024-01-18-19_02_00.json'
compare_file_path = 'tests/example_journal/experiment_journals2024-01-18-19_02_00.json'

def main():
    with open(read_file_path, 'r') as yaml_file:
        experiment = yaml.safe_load(yaml_file)

    experiment_journal = exp.run_experiment(experiment)

    print(f'Writing Journal to File {write_file_path}')
    with open(write_file_path, 'w') as json_file:
        #os.chdir('..')
        json.dump(experiment_journal, json_file, indent=4)

    #with open(compare_file_path, 'r') as json_file:
    #    example_journal = json.dump(example_journal, json_file)

if __name__ == "__main__":
    main()
