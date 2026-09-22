package main

import (
	"fmt"
)

func ping(in <-chan bool, out chan<- int, n int) {
	for i := 0; i < n; i++ {
		<-in // wait for signal from pong or start
		fmt.Printf("ping %d\n", i)
		out <- i // let pong do its job
	}
	close(out) // notify pong of done
}

func pong(in <-chan int, out chan<- bool, done chan<- struct{}) {
	for i := range in { // get i from ping
		fmt.Printf("pong %d\n", i)
		out <- false // let ping do its job
	}
	close(done) // notify main of done
}

func main() {
	pi := make(chan bool, 1) // line B
	po := make(chan int)
	done := make(chan struct{})
	defer close(pi)

	go ping(pi, po, 10)
	go pong(po, pi, done)

	fmt.Println("Start!")
	pi <- true // line A

	<-done
}
