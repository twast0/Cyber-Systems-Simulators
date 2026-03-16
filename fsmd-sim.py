import sys
import xmltodict
from simpleeval import simple_eval, InvalidExpression, NameNotDefined, OperatorNotDefined

class FSMD_Simulator:
    NOP = {'NOP', ''}
    def __init__(self, argv):
        self.states = []
        self.init_state = None
        self.transitions = {}  
        self.variables = {}
        self.inputs = {}
        self.operations = {}
        self.conditions = {}
        self.stimulus = None
        self.max_cycles = 1000
        self.current_state = None
        self.cycle = 0
        # Keep track of what inputs changed this cycle 
        # as to not repeatedly print all inputs
        # including those that are just 0
        self.changed_inputs_this_cycle = set()

        # Parse arguments from commandline
        self.parse_commandline(argv)

        # Open read and save XML data (Description file)
        self.load_model()

        # Loads stim file if one was provided
        self.load_stim()

        # Build a dictionary containing all states, and their possible transition paths (incl. conditions and instructions)
        self.make_transition_table()

        self.current_state = self.init_state

    # Methodified version of code provided for assignment
    def parse_commandline(self, argv):
        if len(argv) < 3:
            print("Usage: python fsmd_sim.py <max_cycles> <model.xml> [stim.xml]")
            sys.exit(1)
        if len(argv) > 4:
            print("Too many arguments given.")
            sys.exit(1)

        self.max_cycles = int(argv[1])
        self.model_file = argv[2]
        self.stim_file = argv[3] if len(argv) == 4 else None

    # Print statements to run in the beginning of the simulation 
    def print_intro(self):
        print("\n Welcome to the FSMD simulator! - Version 5.67" + "\n")
        print("--FSMD description--")

        print("States: ")
        for s in self.states:
            print(f"  { s}")

        print("Initial state:")
        print(f"  {self.init_state}")

        print("Inputs:")
        for key in self.inputs.keys():
            print(f"  {key}")

        print("Variables:")
        for v in self.variables:
            print(f"  {v}")

        print("Operations:")
        for op in self.operations:
            print(f"  {op} : {self.operations[op]}")

        print("Conditions:")
        for cond in self.conditions:
            print(f"  {cond} : {self.conditions[cond]}")

        print("FSMD transitions table:")
        for t in self.transitions:
            print(f"  {t}")
            for transition in self.transitions[t]:
                print(f"    nextstate: {transition['next']}, condition: {transition['cond']}, instruction: {transition['instruction']}")

    def print_sim_start(self):
        print("\n")
        print("---Simulation starting---")
        print("At the beginning of the simulation the status is:")
        self.print_vars()
        print(f"Initial state: {self.init_state}")
        print("-" * 60)

    def print_vars(self, title="Variables:"):
        print(f"{title}")
        for k in sorted(self.variables):
            print(f"  {k} = {self.variables[k]}")

    def print_cycle_start(self):
        print(f"Cycle: {self.cycle}") 
        print(f"Current state: {self.current_state}")

    def print_inputs(self):
        if not self.inputs:
            return
        if self.changed_inputs_this_cycle:
            print(f"Inputs updated in cycle {self.cycle}:")
            for var in sorted(self.changed_inputs_this_cycle):
                if var in self.inputs:
                    print(f"  {var} = {self.inputs[var]}")

    def print_transition(self, cond, instruction, next_state):
        print(f"The condition '{cond}' is true")
        ins = instruction.strip()
        if ins and ins.upper() not in self.NOP:
            print(f"Executing instruction: {ins}")
        print(f"Next state: {next_state}")

    def print_cycle_end(self):
        print(f"At the end of the cycle {self.cycle} execution, the status is:")
        self.print_vars()
        print("-"*60)
        self.changed_inputs_this_cycle.clear()

    def print_finished(self):
        print("\n Reached end-state. Simulation complete. Bye Bye!\n")

    # Loading the Model

    def load_model(self):
        with open(self.model_file) as f:
            data = xmltodict.parse(f.read())['fsmddescription']

        # To avoid re-parsing if need to access data again
        self.model = data

        # States

        # Using .get instead of bracket notation to allow for
        # empty output if doesn't exist, e.g due to formatting
        # error

        self.states = self.no_str_allowed(data.get('statelist', {}).get('state', []))
        self.init_state = data.get('initialstate', '')

        # Inputs & variables (set to 0)
        # Checks that the input list is not empty before trying to access it
        if data['inputlist'] != None:
            for k in self.no_str_allowed(data.get('inputlist', {}).get('input', [])):

        # if k is an empty string (or just contains whitespace)
                if k.strip(): 
                    self.inputs[k.strip()] = 0

        for k in self.no_str_allowed(data.get('variablelist', {}).get('variable', [])):
            if k.strip(): 
                self.variables[k.strip()] = 0

        # Operations
        if data['operationlist'] != None:
            for op in self.envelope_dicts(data.get('operationlist', {}).get('operation', [])):
                n = op.get('name')
                e = op.get('expression')
                if n and e: 
                    self.operations[n] = e.strip()

        # Conditions
        if data['conditionlist'] != None:
            for cd in self.envelope_dicts(data.get('conditionlist', {}).get('condition', [])):
                n = cd.get('name')
                e = cd.get('expression')
                if n and e: 
                    self.conditions[n] = e.strip()

    # Loads in stim file if there is one
    def load_stim(self):
        if not self.stim_file:
            return
        with open(self.stim_file) as f:
            self.stimulus = xmltodict.parse(f.read())

    # Creates a dictionary with the structure -> state: [] for each state
    # appends a dictionary for each transition possible from that state
    # containing condition, instruction and the next state
    def make_transition_table(self):
        self.transitions = {s: [] for s in self.states}
        for state in self.states:
            raw = self.model.get('fsmd', {}).get(state, {}).get('transition', [])
            for t in self.envelope_dicts(raw):
                if not isinstance(t, dict): continue
                self.transitions[state].append({
                    'cond': t.get('condition', 'False'),
                    'instruction': t.get('instruction', 'NOP'),
                    'next': t.get('nextstate', state)
                })

    # Ensure that nothing is stored as a string, or dict
    # Such that navigating the saved information is uniform

    # If parser interprets as string, store in array
    @staticmethod
    def no_str_allowed(val):
        if isinstance(val, str): return [val]
        return val or []
    
    # If parser interprets as dict, same as above
    @staticmethod
    def envelope_dicts(val):
        if isinstance(val, dict): return [val]
        return val or []


    # Allows for evaluation of expressions based on the
    # stored inputs and variables by inputting e.g
    # symbols = self.inputs, or self.variables, etc
    def eval(self, expr: str, symbols: dict):
        try:
            return simple_eval(
                expr,
                names=symbols,
                functions={},               # ← no functions allowed at all
                # You can also disable certain operators if you want ultra-restriction:
                # operators={"+": lambda a,b: a+b}  # only allow +
            )
        except Exception as e:
            print(f"Safe eval failed: {expr} → {type(e).__name__}: {e}")
            return 0
        
    # Applies stimulus if there is one (follow up from load_stim)
    def apply_stimulus(self):
        if not self.stimulus:
            return
        sets = self.stimulus.get('fsmdstimulus', {}).get('setinput', [])
        for item in self.envelope_dicts(sets):
            if str(item.get('cycle', '-1')) == str(self.cycle):
                expr = item.get('expression', '')
                if '=' in expr:
                    var_name = expr.split('=', 1)[0].strip()
                    if var_name:
                        self.changed_inputs_this_cycle.add(var_name)
                self.set_input(expr)

    # Is used to set input values based on the values in the stim file
    def set_input(self, line: str):
        line = line.replace(" ", "")
        if not line or '=' not in line:
            raise ValueError("The input is malformed!")
        try:
            var, rhs = line.split("=", 1)
            val = self.eval(rhs, self.inputs)
            print(self.inputs)
            if var in self.inputs:
                self.inputs[var] = val
        except Exception as e:
            raise ValueError(f"Input error: {e}")
        
    # Is used to go through each operation in an instruction
    # and run the self.execute_operation on it (unless its NOP or similar)
    def execute_instruction(self, instr: str):
        if not instr or instr.strip().upper() in self.NOP:
            return
        for part in instr.split():
            if part in self.operations:
                self.execute_operation(self.operations[part])

    # Checks that the operation is valid
    # Runs it using the combined dictionary of the variables
    # and inputs (also variables but from input) as the local space
    # Updates the relevant variable
    def execute_operation(self, op_str: str):
        op_str = op_str.replace(" ", "")
        if '=' not in op_str:
            raise ValueError(f"Operation {op_str} is malformed")
        try:
            target, rhs = op_str.split("=", 1)
            val = self.eval(rhs, {**self.variables, **self.inputs})
            if target in self.variables:
                self.variables[target] = val
        except Exception as e:
            raise ValueError(f"Operation error: {e}")


    # Evaluates conditions also based on the combined
    # local space of the variables and inputs as the
    # local/"known" space
    def evaluate_condition(self, cond: str):
        c = cond.lower().strip()
        if c in ('true', '1'):   return True
        if c in ('false', '0'):  return False

        expr = cond
        for name, body in self.conditions.items():
            expr = expr.replace(name, f"({body})")

        return bool(self.eval(expr, {**self.variables, **self.inputs}))

    # Goes through the current state's transitions, evaluates conditions
    # if a condition is true, executes the associated instruction
    # and returns the next state (unless there are no transitions)
    # then returns the current state
    def take_step(self):
        for tr in self.transitions.get(self.current_state, []):
            if self.evaluate_condition(tr['cond']):
                self.print_transition(tr['cond'], tr['instruction'], tr['next'])
                self.execute_instruction(tr['instruction'])
                return tr['next']
        return self.current_state

    # Checks for end states, primarily in the stimulus file,
    # if there is no stimulus file, assumes that the last state
    # defined in the description xml is the end state
    def reached_end(self):
        if not self.stimulus and not self.states:
            raise ValueError("There appears to be no states")
        elif not self.stimulus:
            ends = self.states[-1]
        else:
            end = self.stimulus.get('fsmdstimulus', {}).get('endstate', '')
            ends = set(end.split() if isinstance(end, str) else end)
        if ends == '':
            raise ValueError("End state is not defined")
        return self.current_state in ends


    # Main loop that runs the simulator
    def run(self):
        self.print_intro()
        self.print_sim_start()

        while self.cycle < self.max_cycles:
            self.print_cycle_start()
            self.apply_stimulus()
            self.print_inputs()
            next_state = self.take_step()
            self.current_state = next_state
            self.print_cycle_end()

            if self.reached_end():
                self.print_finished()
                return
            self.cycle += 1

        print(f"\nReached maximum of {self.max_cycles} cycles — stopping.\n")

    # Entry-point method that allows the class to be run 
    # directly in commandline
    @classmethod
    def main(cls):
        sim = cls(sys.argv)
        sim.run()


if __name__ == "__main__":
    FSMD_Simulator.main()