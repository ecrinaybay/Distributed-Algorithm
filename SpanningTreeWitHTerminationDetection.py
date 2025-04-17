import random
import sys

sys.path.insert(1, '.')
from source import DawnSimVis

# Root node that will initiate the spanning tree construction
ROOT = 0

# States
IDLE = "IDLE"
XPLORD = "XPLORD"
TERM = "TERM"

# Message types
PROBE = "probe"
ACK = "ack"
REJECT = "reject"


###########################################################
class Node(DawnSimVis.BaseNode):

    ###################
    def init(self):
        # Initialize node state and variables
        self.currstate = IDLE  # Current state of the node
        self.parent = -1  # Parent node in the spanning tree
        self.childs = set()  # Children nodes in the spanning tree
        self.others = set()  # Other neighbors (not parent or children)
        self.pending_responses = set()  # Neighbors we're waiting to hear from

        # Color the node based on its initial state (IDLE)
        self.change_color(0.8, 0.8, 1.0)  # Light blue for IDLE

    ###################
    def run(self):
        # If this is the root node, start the algorithm
        if self.id == ROOT:
            self.log("Root node starting algorithm")
            # Change state to XPLORD
            self.currstate = XPLORD
            self.change_color(0.0, 0.7, 0.0)  # Green for XPLORD

            # Broadcast probe to all neighbors
            self.broadcast_probe()

    ###################
    def on_receive(self, pck):
        msg_type = pck["type"]
        sender = pck["sender"]

        self.log(f"Received {msg_type} from {sender}, current state: {self.currstate}")

        # Handle message based on current state
        if self.currstate == IDLE:
            if msg_type == PROBE:
                # First time receiving a probe
                self.parent = sender
                self.log(f"Setting parent to {self.parent}")

                # Move to XPLORD state
                self.currstate = XPLORD
                self.change_color(0.0, 0.7, 0.0)  # Green for XPLORD

                # Broadcast probe to all neighbors except parent
                self.broadcast_probe()

                # If no neighbors to wait for, immediately send ACK to parent
                if len(self.pending_responses) == 0:
                    self.send_ack_to_parent()

        elif self.currstate == XPLORD:
            if msg_type == PROBE:
                # Already received a probe before, reject this one
                self.send(sender, {"type": REJECT, "sender": self.id})

            elif msg_type == ACK:
                # Add sender to children set
                self.childs.add(sender)
                self.pending_responses.remove(sender)
                self.log(f"Added {sender} to children, pending: {self.pending_responses}")

                # Visual indication of parent-child relationship
                self.sim.scene.dellink(self.id, sender, "edge")
                self.sim.scene.addlink(self.id, sender, "prev")

                # Check if we've heard from all neighbors
                self.check_completion()

            elif msg_type == REJECT:
                # Add sender to others set
                self.others.add(sender)
                self.pending_responses.remove(sender)
                self.log(f"Added {sender} to others, pending: {self.pending_responses}")

                # Check if we've heard from all neighbors
                self.check_completion()

        # In TERM state, we ignore all messages

    ###################
    def broadcast_probe(self):
        """Broadcast probe message to all neighbors except parent"""
        # Get all neighbors within transmission range
        neighbors = []
        for dist, node in self.neighbor_distance_list:
            if dist <= self.tx_range and node.id != self.parent:
                neighbors.append(node.id)

        # Set up pending responses
        self.pending_responses = set(neighbors)
        self.log(f"Waiting for responses from: {self.pending_responses}")

        # Broadcast probe message
        if neighbors:
            message = {"type": PROBE, "sender": self.id}
            for neighbor in neighbors:
                self.send(neighbor, message)

    ###################
    def check_completion(self):
        """Check if we've heard from all neighbors and can send ACK to parent"""
        if not self.pending_responses:
            self.log(f"All neighbors responded: children={self.childs}, others={self.others}")

            # Send ACK to parent if not root
            self.send_ack_to_parent()

            # Move to TERM state
            self.currstate = TERM
            self.change_color(1.0, 0.5, 0.0)  # Orange for TERM
            self.log("Node terminated")

    ###################
    def send_ack_to_parent(self):
        """Send ACK message to parent if not root"""
        if self.parent != -1:
            self.send(self.parent, {"type": ACK, "sender": self.id})
            self.log(f"Sent ACK to parent {self.parent}")

    ###################
    def finish(self):
        """Print final state information"""
        self.log(f"Final state: {self.currstate}")
        self.log(f"Parent: {self.parent}")
        self.log(f"Children: {self.childs}")
        self.log(f"Others: {self.others}")


###########################################################
def create_network():
    # place nodes over 10x10 grids
    for x in range(10):
        for y in range(10):
            px = 50 + x * 60 + random.uniform(-20, 20)
            py = 50 + y * 60 + random.uniform(-20, 20)
            sim.add_node(Node, pos=(px, py), tx_range=75)


# setting the simulation
sim = DawnSimVis.Simulator(
    duration=100,
    timescale=1,
    visual=True,
    terrain_size=(650, 650),
    title='Asynchronous Spanning Tree with Termination Detection')

# creating network
create_network()

# start the simulation
sim.run()