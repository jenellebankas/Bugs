var coll = document.getElementsByClassName("collapsible");
var i;

for (i = 0; i < coll.length; i++) {
    coll[i].addEventListener("click", function () {
        this.classList.toggle("active");
        var content = this.nextElementSibling;
        if (content.style.maxHeight) {
            content.style.maxHeight = null;
        } else {
            content.style.maxHeight = content.scrollHeight + "px";
        }
    });
}

// DO NOT REMOVE
// fills journey id and cost when booking a journey. 
window.prefillCostAndID = function (button) {

    const cost = button.getAttribute('data-cost');

    // find the cost in modal and fill
    const costInput = document.getElementById('costInput');
    if (costInput) {
        costInput.value = cost;
        console.log('Cost filled successfully!');
    }

    const journey_id = button.getAttribute('data-journey-id')

    // find journey id in modal and fill
    const journeyIDInput = document.getElementById('journeyIDInput');
    if (journeyIDInput) {
        journeyIDInput.value = journey_id;
        console.log('Journey ID filled successfully!');
    }

    const booking_id = button.getAttribute('data-booking-id')

    // find journey id in modal and fill
    const bookingIDInput = document.getElementById('bookingIDInput');
    if (bookingIDInput) {
        bookingIDInput.value = booking_id;
        console.log('Booking ID filled successfully!');
    }

};

//for editing locations
// Populate modal fields in modal editLocationModal
function populateModal(locationId) {
    fetch(`/get-location-details/${locationId}`)
      .then(response => response.json())
      .then(details => {
        document.getElementById('nickname').value = details.nickname || "";
        document.getElementById('addressLine1').value = details.addressLine1 || "";
        document.getElementById('city').value = details.city || "";
        document.getElementById('postcode').value = details.postcode || "";
        document.getElementById('country').value = details.country || "";
        
        //set location id for when confirm button is pressed and details are edited
        const confirmButton = document.getElementById('edit_location_btn');
        confirmButton.setAttribute('data-location-id', locationId);
      })
      .catch(error => console.error('Error fetching location details:', error));
  }
  
function editLocation(button, journey_id) {

    //get location id from confirm button attrubute
    const location_id = button.getAttribute('data-location-id');

    //get edited data
    const locationData = {
        nickname: document.getElementById('nickname').value,
        addressLine1: document.getElementById('addressLine1').value,
        city: document.getElementById('city').value,
        postcode: document.getElementById('postcode').value,
        country: document.getElementById('country').value,
    };

    //send to views.py function to update in database
    fetch(`/edit_location/${location_id}/${journey_id}`, {
        method: 'PUT', 
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': document.querySelector('input[name="csrf_token"]').value,
        },
        body: JSON.stringify(locationData),
    })

    .then(response => {
        if (response.status === 204) {
            //success
            window.location.reload();
        }
    })
}


// for adding locations
$(document).ready(function () {

    $("#add_location_btn").click(function () {
        let nickname = $("#nickname").val().trim();
        let addressLine1 = $("#addressLine1").val().trim();
        let country = $("#country").val().trim();
        let city = $("#city").val().trim();
        let postcode = $("#postcode").val().trim();
        let csrf_token = $("input[name='csrf_token']").val();  // Get CSRF token from form

        if (!nickname || !addressLine1 || !country || !city || !postcode) {
            showFlashMessage("All Location Fields Must be Filled", "error");
            return;
        }

        $.ajax({
            url: "/add_location",
            type: "POST",
            contentType: "application/json",
            headers: {"X-CSRFToken": csrf_token},
            data: JSON.stringify({
                nickname: nickname,
                addressLine1: addressLine1,
                country: country,
                city: city,
                postcode: postcode
            }),
            success: function (response) {
                if (response.success) {
                    showFlashMessage("Location Added!", "success");
                    $("#previous_pickup_location").append(`<option value="${response.id}">${response.nickname}</option>`);
                    $("#previous_dropoff_location").append(`<option value="${response.id}">${response.nickname}</option>`);

                    // Clear form fields
                    $("#nickname, #addressLine1, #country, #city, #postcode").val("");

                    // Close modal
                    $("#addLocationModal").modal("hide");
                } else {
                    let errorMessage = flash_error.responseJSON ? flash_error.responseJSON.message : "Error Adding Location";
                    showFlashMessage(errorMessage, "error");
                }
            },
            error: function (flash_error) {
                let errorMessage = flash_error.responseJSON ? flash_error.responseJSON.message : "An unexpected error occurred";
                showFlashMessage(errorMessage, "error");
            }
        });
    });
})

// for adding a review for the driver
$(document).ready(function () {
    var bookingId;

    $("#add_booking_id_btn").click(function () {
        bookingId = $(this).data('booking-id');
    });


    $("#add_review_btn").click(function () {

        let review_title = $("#review_title").val().trim();
        let comment = $("#comment").val().trim();
        let rating = $("#rating").val().trim();
        let csrf_token = $("input[name='csrf_token']").val();

        $.ajax({
            url: "/driver-review/" + bookingId,
            type: "POST",
            contentType: "application/json",
            headers: {"X-CSRFToken": csrf_token},
            data: JSON.stringify({
                review_title: review_title,
                comment: comment,
                rating: rating,
            }),
            success: function (response) {
                showFlashMessage(response.message, "success");
                if (response.success) {
                    // hide adding review button and closing modal
                    $("#add_booking_id_btn").hide();
                    $("#makeReviewModal").modal("hide");
                } else {
                    showFlashMessage("Error Adding Review", "error");
                }
            }, error: function (flash_error) {
                let errorMessage = flash_error.responseJSON ? flash_error.responseJSON.message : "An unexpected error occurred";
                showFlashMessage(errorMessage, "error");
            }
        });
    });
})

// for viewing modal for the driver side
$(document).ready(function () {
    $('#viewReviewModal').on('show.bs.modal', function (event) {
        var button = $(event.relatedTarget);
        var journeyId = button.data('journey-id');

        $.ajax({
            url: '/get_review/' + journeyId,
            method: 'GET',
            success: function (data) {
                if (data.success) {
                    var reviewsContainer = $('#reviews_list');
                    reviewsContainer.empty();

                    data.reviews.forEach(function (review) {
                        var reviewHtml = `
                            <div class="card border p-2 mb-2">
                                <h5>${review.review_title}</h5>
                                <p><strong>Comment:</strong> ${review.comment}</p>
                                <p><strong>Rating:</strong> ${review.rating} ⭐</p>
                            </div>`;
                        reviewsContainer.append(reviewHtml);
                    });
                } else {
                    $('#reviews_list').html('<p>No reviews yet</p>');
                }
            }, error: function (flash_error) {
                let errorMessage = flash_error.responseJSON ? flash_error.responseJSON.message : "An unexpected error occurred";
                showFlashMessage(errorMessage, "error");
            }
        });
    });
})

// show flash errors instead of json errors
function showFlashMessage(message, category) {
    let flashDiv = `<div class="alert alert-${category} alert-dismissible fade show" role="alert">
                        ${message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>`;
    $(".messages").append(flashDiv);
}



// for deleting locations
$(document).ready(function () {
  var $grid = $('.row').isotope({
      itemSelector: '.column',
      layoutMode: 'masonry'
  });

  $(".delete-btn").click(function () {
      var locationId = $(this).data("id");
      var card = $("#location_" + locationId);
      let csrf_token = $("input[name='csrf_token']").val();

      Swal.fire({
          title: "Are you sure?",
          text: "This location will be permanently deleted!",
          icon: "warning",
          showCancelButton: true,
          confirmButtonColor: "#d33",
          cancelButtonColor: "#3085d6",
          confirmButtonText: "Yes, delete it!"
      }).then((result) => {
          if (result.isConfirmed) {

              $.ajax({
                  url: `/delete/${locationId}`,
                  type: "POST",
                  contentType: "application/json",
                  headers: {"X-CSRFToken": csrf_token},
                  success: function (response) {
                      $grid.isotope('remove', card).isotope('layout');
                      console.log($grid.children('.column').length)
                      if ($grid.children('.column').length === 0) {
                          location.reload();
                      }
                  },
                  error: function (xhr) {
                      Swal.fire("Error", "Failed to delete location.", "error");
                  }
              });
          }
      });
  });
});

// auto location
let autocomplete;

function initAutocomplete() {
  const input = document.getElementById("autocomplete");
  const autocomplete = new google.maps.places.Autocomplete(input);
  autocomplete.setFields(["address_components"]);

  autocomplete.addListener("place_changed", () => {
    const place = autocomplete.getPlace();
    const components = place.address_components;

    let street = "", city = "", postcode = "", country = "";

    if (components) {
      for (const comp of components) {
        const types = comp.types;
        if (types.includes("street_number")) street = comp.long_name + " ";
        if (types.includes("route")) street += comp.long_name;
        if (types.includes("locality") || types.includes("postal_town")) city = comp.long_name;
        if (types.includes("postal_code")) postcode = comp.long_name;
        if (types.includes("country")) country = comp.long_name;
      }
      // If street is still empty, use first part of formatted address
      if (!street && place.formatted_address) {
        const firstPart = place.formatted_address.split(",")[0];
        street = firstPart;
      }
      
      
      document.getElementById("addressLine1").value = street;
      document.getElementById("city").value = city;
      document.getElementById("postcode").value = postcode;
      document.getElementById("country").value = country;
    }else {
      console.warn("No address components found.");
    }

  });
}
document.addEventListener("DOMContentLoaded", () => {
  initAutocomplete();
});

document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("addLocationModal");
  if (modal) {
    modal.addEventListener("shown.bs.modal", () => {
      // Re-initialize autocomplete now that input is visible
      initAutocomplete(); 
      
      // Also focus the input so suggestions appear on typing
      document.getElementById("autocomplete").focus();
    });
  }
});

// script.js - Fixing Dynamic Route Updates & Buttons

let map;
let directionsService;
let directionsRenderer;
let geocoder;

document.addEventListener("DOMContentLoaded", function () {
    initMap();

    document.querySelectorAll(".show-route-btn").forEach(button => {
        button.addEventListener("click", function () {
            const pickupAddress = this.getAttribute("data-pickup");
            const dropoffAddress = this.getAttribute("data-dropoff");
            showDynamicRouteByAddress(pickupAddress, dropoffAddress);
        });
    });
});

function initMap() {
    const defaultCenter = { lat: 51.5074, lng: -0.1278 }; // London
    map = new google.maps.Map(document.getElementById("map"), {
        center: defaultCenter,
        zoom: 5,
    });

    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer();
    directionsRenderer.setMap(map);

    geocoder = new google.maps.Geocoder();
}

function showDynamicRouteByAddress(pickupAddress, dropoffAddress) {
    Promise.all([
        geocodeAddress(pickupAddress),
        geocodeAddress(dropoffAddress),
    ])
    .then(([pickupCoords, dropoffCoords]) => {
        const request = {
            origin: pickupCoords,
            destination: dropoffCoords,
            travelMode: google.maps.TravelMode.DRIVING,
        };

        directionsService.route(request, (result, status) => {
            if (status === google.maps.DirectionsStatus.OK) {
                directionsRenderer.setDirections(result);
            } else {
                console.error("Directions error:", status);
            }
        });
    })
    .catch(error => {
        console.error("Geocoding error:", error);
    });
}

function geocodeAddress(address) {
    return new Promise((resolve, reject) => {
        geocoder.geocode({ address: address }, (results, status) => {
            if (status === google.maps.GeocoderStatus.OK && results[0]) {
                resolve(results[0].geometry.location);
            } else {
                reject(`Geocode failed for ${address}: ${status}`);
            }
        });
    });
}