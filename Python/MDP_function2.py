import collections
import numpy as np
import pandas
import mdptoolbox, mdptoolbox.example
import argparse


def generate_MDP_input2(original_data, features):

    students_variables = ['student', 'priorTutorAction', 'reward']

    # generate distinct state based on feature
    #original_data['state'] = original_data[features].apply(lambda x: ':'.join(str(v) for v in x), axis=1)
    original_data['state'] = original_data[features].apply(tuple, axis=1)
    students_variables = students_variables + ['state']
    data = original_data[students_variables]

    # quantify actions
    distinct_acts = list(data['priorTutorAction'].unique())
    Nx = len(distinct_acts)
    i = 0
    for act in distinct_acts:
        data.loc[data['priorTutorAction'] == act, 'priorTutorAction'] = i
        i += 1

    # initialize state transition table, expected reward table, starting state table
    # distinct_states didn't contain terminal state
    student_list = list(data['student'].unique())
    distinct_states = list()
    for student in student_list:
        student_data = data.loc[data['student'] == student,]
        # don't consider last row
        temp_states = list(student_data['state'])[0:-1]
        distinct_states = distinct_states + temp_states
    distinct_states = list(set(distinct_states))

    Ns = len(distinct_states)

    # we include terminal state
    start_states = np.zeros(Ns + 1)
    A = np.zeros((Nx, Ns+1, Ns+1))
    expectR = np.zeros((Nx, Ns+1, Ns+1))

    # update table values episode by episode
    # each episode is a student data set
    for student in student_list:
        student_data = data.loc[data['student'] == student,]
        row_list = student_data.index.tolist()

        # count the number of start state
        start_states[distinct_states.index(student_data.loc[row_list[0], 'state'])] += 1

        # count the number of transition among states without terminal state
        for i in range(1, (len(row_list)-1)):
            state1 = distinct_states.index(student_data.loc[row_list[i - 1], 'state'])
            state2 = distinct_states.index(student_data.loc[row_list[i], 'state'])
            act = student_data.loc[row_list[i], 'priorTutorAction']

            # count the state transition
            A[act, state1, state2] += 1
            expectR[act, state1, state2] += float(student_data.loc[row_list[i], 'reward'])

        # count the number of transition from state to terminal
        state1 = distinct_states.index(student_data.loc[row_list[-2], 'state'])
        act = student_data.loc[row_list[-1], 'priorTutorAction']
        A[act, state1, Ns] += 1
        expectR[act, state1, Ns] += float(student_data.loc[row_list[-1], 'reward'])

    # normalization
    start_states = start_states / np.sum(start_states)

    for act in range(Nx):
        A[act, Ns, Ns] = 1
        # generate expected reward
        with np.errstate(divide='ignore', invalid='ignore'):
            expectR[act] = np.divide(expectR[act], A[act])
            expectR[np.isnan(expectR)] = 0

        # each column will sum to 1 for each row, obtain the state transition table
        for l in np.where(np.sum(A[act], axis=1) == 0)[0]:
            A[act][l][l] = 1
        A[act] = np.divide(A[act].transpose(), np.sum(A[act], axis=1))
        A[act] = A[act].transpose()

    return [start_states, A, expectR, distinct_acts, distinct_states]


def calcuate_ECR(start_states, expectV):
    ECR_value = start_states.dot(np.array(expectV))
    return ECR_value


def output_policy(distinct_acts, distinct_states, vi):
    Ns = len(distinct_states)
    print('Policy: ')
    print('state -> action, value-function')
    countwe = 0
    countps = 0
    for s in range(Ns):
        if (str(distinct_acts[vi.policy[s]]) == 'WE'):
            countwe += 1
        elif (str(distinct_acts[vi.policy[s]]) == 'PS'):
            countps += 1
        print(str(distinct_states[s]) + " -> " + str(distinct_acts[vi.policy[s]]) + ", " + str(vi.V[s]))
    print countwe
    print countps
    print Ns

def checkFeatures(original_data):
    cols = list(original_data.columns)

    max_ecr = 0.0
    max_selected_features = []
    for i in range(7, len(cols)):
        if (original_data[cols[i]].dtype == 'int64' and cols[i] != 'cumul_Interaction'):# and len(set(original_data[cols[i]])) <= 10):
            selected_features = ['cumul_Interaction', cols[i]]
            #print selected_features
            #selected_features = ['Level', 'probDiff']
            ecr = induce_policy_MDP2(original_data, selected_features)
            if (ecr > max_ecr):
                max_ecr = ecr
                max_selected_features = selected_features
    print max_selected_features
    return max_ecr


def induce_policy_MDP2(original_data, selected_features):

    print(selected_features)
    [start_states, A, expectR, distinct_acts, distinct_states] = generate_MDP_input2(original_data, selected_features)

    # apply Value Iteration to run the MDP
    vi = mdptoolbox.mdp.ValueIteration(A, expectR, 0.9)
    vi.run()

    # output policy
    output_policy(distinct_acts, distinct_states, vi)

    # evaluate policy using ECR
    ECR_value = calcuate_ECR(start_states, vi.V)
    print('ECR value: ' + str(ECR_value))
    return ECR_value

if __name__ == "__main__":

    original_data = pandas.read_csv('data/MDP_Original_data2.csv')
    famd_data = pandas.read_csv('data/famd/FAMD_features.csv')
    x = pandas.cut(famd_data['Dim.6'], 2, labels=False)
    two_features = original_data[['Level', 'cumul_Interaction']]

    nn_data = pandas.read_csv('data/nn/nn_scrap/nn_discreitized_data.csv')
    selected_features = ['Level', 'cumul_Interaction', 'Dim.6']
    total_data = pandas.concat([original_data.iloc[:,0:6], two_features, x], axis=1)
    #selected_features = ['symbolicRepresentationCount']
    ECR_value = induce_policy_MDP2(total_data, selected_features)
    #print checkFeatures(original_data)
