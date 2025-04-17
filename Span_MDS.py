import random
import sys

sys.path.insert(1, '.')
from source import DawnSimVis

# Message types
ROUND = 'round'
CH_BLACK = 'ch_black'
CH_GRAY = 'ch_gray'
UNDECIDE = 'undecide'
NO_CHANGE = 'no_change'
CONFIRM = 'confirm'  # Onay mesajı ekledim

# Node colors
WHITE = 'white'
BLACK = 'black'
GRAY = 'gray'


###########################################################
class Node(DawnSimVis.BaseNode):

    ###################
    def init(self):
        # Initialize node variables
        self.color = WHITE
        self.neigh_cols = {}  # neighbor colors
        self.spans = 0  # span counter
        self.received = set()  # set of received nodes
        self.recvd_cols = set()  # received colors
        self.lost_neighs = set()  # lost neighbors
        self.curr_neighs = set()  # current neighbors
        self.round_recvd = False
        self.round_over = False
        self.finished = False
        self.n_recvd = 0
        self.current_round = 0
        self.max_rounds = 20  # Sonsuz döngüyü önlemek için
        self.black_conflicts = set()  # Siyah düğüm çakışmalarını takip etmek için

        # Get initial neighbor information
        for dist, node in self.neighbor_distance_list:
            if dist <= self.tx_range:
                self.curr_neighs.add(node.id)
                self.neigh_cols[node.id] = WHITE

        # Calculate initial span
        self.spans = len(self.curr_neighs) + 1

        # Visual representation
        self.change_visual_color()

    ###################
    def change_visual_color(self):
        if self.color == WHITE:
            self.change_color(1, 1, 1)  # white
        elif self.color == BLACK:
            self.change_color(0, 0, 0)  # black
        elif self.color == GRAY:
            self.change_color(0.5, 0.5, 0.5)  # gray

    ###################
    def run(self):
        # Start the algorithm by initiating round 1
        self.current_round = 1
        self.start_round()

    ###################
    def start_round(self):
        self.log(f"Starting round {self.current_round}")
        self.round_recvd = False
        self.received.clear()
        self.black_conflicts.clear()

        # Send round message to neighbors
        pck = {
            'type': ROUND,
            'round': self.current_round,
            'sender': self.id,
            'spans': self.spans,
            'color': self.color  # Renk bilgisini de ekleyelim
        }
        self.send(DawnSimVis.BROADCAST_ADDR, pck)

        # Karar vermek için biraz bekle
        self.set_timer(1, self.make_decision)

    ###################
    def make_decision(self):
        if self.finished:
            return

        # Check if we already have a black neighbor
        has_black_neighbor = False
        for nid, color in self.neigh_cols.items():
            if color == BLACK:
                has_black_neighbor = True
                break

        if has_black_neighbor and self.color == WHITE:
            # Komşu siyahsa, biz gri olalım
            self.color = GRAY
            self.change_visual_color()

            pck = {
                'type': CH_GRAY,
                'sender': self.id,
                'round': self.current_round,
                'color': GRAY
            }
            self.send(DawnSimVis.BROADCAST_ADDR, pck)
            return

        # If we are white and have highest span, become black
        if self.color == WHITE and self.spans != 0:
            has_highest_span = True
            for nid in self.curr_neighs:
                if nid in self.received:
                    neighbor_span = getattr(self, 'neighbor_spans', {}).get(nid, 0)
                    # Eşitlik durumunda düğüm ID'lerine bakarak belirle
                    if self.spans < neighbor_span or (self.spans == neighbor_span and self.id < nid):
                        has_highest_span = False
                        break

            if has_highest_span:
                self.log(f"Node {self.id} has highest span ({self.spans}), coloring BLACK")
                self.color = BLACK
                self.spans = 0
                self.change_visual_color()

                pck = {
                    'type': CH_BLACK,
                    'sender': self.id,
                    'round': self.current_round,
                    'color': BLACK
                }
                self.send(DawnSimVis.BROADCAST_ADDR, pck)
            else:
                pck = {
                    'type': UNDECIDE,
                    'sender': self.id,
                    'round': self.current_round,
                    'color': self.color
                }
                self.send(DawnSimVis.BROADCAST_ADDR, pck)
        else:
            # No change
            pck = {
                'type': NO_CHANGE,
                'sender': self.id,
                'round': self.current_round,
                'color': self.color
            }
            self.send(DawnSimVis.BROADCAST_ADDR, pck)

        # Onay fazına geç
        self.set_timer(1, self.send_confirmation)

    ###################
    def send_confirmation(self):
        if self.finished:
            return

        # Send confirmation with current color
        pck = {
            'type': CONFIRM,
            'sender': self.id,
            'round': self.current_round,
            'color': self.color
        }
        self.send(DawnSimVis.BROADCAST_ADDR, pck)

        # Çakışmaları çözmek için zamanlayıcı ayarla
        self.set_timer(1, self.resolve_conflicts)

    ###################
    def resolve_conflicts(self):
        if self.finished:
            return

        # Siyah-siyah çakışmalarını çöz
        if self.color == BLACK and len(self.black_conflicts) > 0:
            for conflict_id in self.black_conflicts:
                # ID'si küçük olan siyah kalır, diğeri gri olur
                if self.id > conflict_id:
                    self.log(f"Node {self.id} changing to GRAY due to conflict with node {conflict_id}")
                    self.color = GRAY
                    self.change_visual_color()

                    # Değişikliği bildir
                    pck = {
                        'type': CH_GRAY,
                        'sender': self.id,
                        'round': self.current_round,
                        'color': GRAY
                    }
                    self.send(DawnSimVis.BROADCAST_ADDR, pck)
                    break

        # Phase 2: Check if neighbors are black
        if self.color == WHITE:
            for nid, col in self.neigh_cols.items():
                if col == BLACK:
                    self.log(f"Node {self.id} changing to GRAY due to BLACK neighbor {nid}")
                    self.color = GRAY
                    self.change_visual_color()

                    pck = {
                        'type': CH_GRAY,
                        'sender': self.id,
                        'round': self.current_round,
                        'color': GRAY
                    }
                    self.send(DawnSimVis.BROADCAST_ADDR, pck)
                    break

        # Turu bitir
        self.set_timer(1, self.finish_round)

    ###################
    def finish_round(self):
        if self.finished:
            return

        # Update spans for next round
        for nid, col in self.neigh_cols.items():
            if col != WHITE:
                # Node is not white, remove from span count
                if nid not in self.lost_neighs:
                    self.lost_neighs.add(nid)

        # Remove lost neighbors
        self.curr_neighs -= self.lost_neighs

        # İzole düğümleri zorla siyah yap
        if len(self.curr_neighs) == 0 and self.color == WHITE:
            self.color = BLACK
            self.change_visual_color()
            self.finished = True
            self.log(f"Isolated node {self.id} colored BLACK and FINISHED")

        # Maksimum tur kontrolü
        if self.current_round >= self.max_rounds:
            if self.color == WHITE:
                # Beyaz kalmış düğümleri zorla siyah yap
                self.color = BLACK
                self.change_visual_color()
                self.log(f"Node {self.id} forced BLACK after max rounds")
            self.finished = True

        # Algoritma bitişini kontrol et
        if self.color != WHITE:
            # Gri veya siyah düğümler için tüm komşuların renklenmesini kontrol et
            all_colored = True
            for nid in self.curr_neighs:
                if self.neigh_cols.get(nid) == WHITE:
                    all_colored = False
                    break

            if all_colored:
                self.finished = True
                self.log(f"Node {self.id} FINISHED with color {self.color}")

        # Sonraki turu başlat
        if not self.finished:
            self.current_round += 1
            self.lost_neighs.clear()
            self.set_timer(1, self.start_round)

    ###################
    def on_receive(self, pck):
        msg_type = pck.get('type')
        sender = pck.get('sender')
        sender_color = pck.get('color')

        # Komşunun rengini güncelle
        if sender_color and sender in self.curr_neighs:
            self.neigh_cols[sender] = sender_color

        if msg_type == ROUND:
            # Store neighbor span information for comparison
            if not hasattr(self, 'neighbor_spans'):
                self.neighbor_spans = {}
            self.neighbor_spans[sender] = pck.get('spans', 0)
            self.received.add(sender)

        elif msg_type == CONFIRM:
            # Onay mesajını işle
            if sender_color == BLACK and self.color == BLACK:
                # İki komşu siyah, çakışma var
                self.black_conflicts.add(sender)
                self.log(f"Black conflict detected with node {sender}")

        elif msg_type == CH_BLACK:
            # Update neighbor color to black
            self.neigh_cols[sender] = BLACK
            self.recvd_cols.add(BLACK)
            self.received.add(sender)

            # Beyaz düğüm için span güncelle
            if self.color == WHITE:
                self.spans -= 1

            # Beyaz düğüm ve komşu siyahsa, hemen gri ol
            if self.color == WHITE:
                self.log(f"Node {self.id} immediately changing to GRAY due to BLACK neighbor {sender}")
                self.color = GRAY
                self.change_visual_color()

                pck = {
                    'type': CH_GRAY,
                    'sender': self.id,
                    'round': self.current_round,
                    'color': GRAY
                }
                self.send(DawnSimVis.BROADCAST_ADDR, pck)

        elif msg_type == UNDECIDE:
            # Kararsız komşu
            self.received.add(sender)

        elif msg_type == CH_GRAY:
            # Update neighbor color to gray
            self.neigh_cols[sender] = GRAY
            self.received.add(sender)

            # Beyaz düğüm için span güncelle
            if self.color == WHITE:
                self.spans -= 1

        elif msg_type == NO_CHANGE:
            # Değişmeyen komşu
            self.received.add(sender)


###########################################################
def create_network():
    # place nodes over 100x100 grids
    for x in range(10):
        for y in range(10):
            px = 50 + x * 60 + random.uniform(-20, 20)
            py = 50 + y * 60 + random.uniform(-20, 20)
            sim.add_node(Node, pos=(px, py), tx_range=75)


# setting the simulation
sim = DawnSimVis.Simulator(
    duration=200,
    timescale=1,
    visual=True,
    terrain_size=(650, 650),
    title='Improved Span_MDS Algorithm')

# creating network
create_network()

# start the simulation
sim.run()