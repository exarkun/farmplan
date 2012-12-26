jQuery.noConflict();
jQuery(document).ready(function() {
    /* Get Underscore.js to give up the global name _ */
    var underscore = _.noConflict();

    function template(id) {
        return underscore.template(jQuery(id).html());
    }

    var Crop = Backbone.Model.extend({
        urlRoot: "../api/crops",
        defaults: {
            id: null,
            name: "",
            description: "",
            picture: "",
            yield_lbs_per_bed_foot: "",
            rows_per_bed: "",
            in_row_spacing: "",
            row_feet_per_oz_seed: "",
            harvest_weeks: ""}});

    var CropPlan = Backbone.Collection.extend({
        model: Crop,
        url: "../api/crops"});

    var CropPlanView = Backbone.View.extend({
        tagName: "ul",

        initialize: function initialize() {
            var self = this;
            this.model.bind("reset", this.render, this);
            this.model.bind("add", function addCrop(crop) {
                jQuery(self.el).append(new CropPlanItemView({model: crop}).render().el);
            });
        },

        render: function renderCropPlanView() {
            underscore.each(this.model.models, function renderOneCrop(crop) {
                jQuery(this.el).append(new CropPlanItemView({model: crop}).render().el);
            }, this);
            return this;
        }});

    var CropPlanItemView = Backbone.View.extend({
        tagName: "li",
        template: template("#template-crop-plan-item"),

        initialize: function initializeCropPlanItemView() {
            this.model.bind("change", this.render, this);
            this.model.bind("destroy", this.close, this);
        },

        render: function renderCropPlanItemView() {
            jQuery(this.el).html(this.template(this.model.toJSON()));
            return this;
        },

        close: function closeCropPlanItemView() {
            jQuery(this.el).unbind();
            jQuery(this.el).remove();
        }});

    var CropView = Backbone.View.extend({
        template: template("#template-crop-details"),

        initialize: function initializeCropView () {
            this.model.bind("change", this.render, this);
        },

        render: function renderCropView() {
            jQuery(this.el).html(this.template(this.model.toJSON()));
            return this;
        },

        events: {
            "click .save": "saveCrop",
            "click .delete": "deleteCrop"
        },

        _syncOptions: function _syncOptions() {
            var status = jQuery("#status-communicating");
            var options = {
                wait: true,
                status: status,
                success: function() {
                    status.css("display", "none");
                },
                error: function(model, xhr, options) {
                    status.css("display", "none");
                    alert("Problem synchronizing with server; values not saved.");
                }};
            return options;
        },

        saveCrop: function saveCrop() {
            var attributes = {};
            for (var field in this.model.defaults) {
                if (field == "id") {
                    continue;
                }
                attributes[field] = jQuery("#" + field).val();
            }
            /* TODO Check for success or failure on this - and on failure,
             * revert view changes? */
            this.model.set(attributes);

            /* Let the user know some network operation is happening */
            var options = self._syncOptions();
            options.status.css("display", "block");

            if (this.model.isNew()) {
                app.cropPlan.create(this.model, options);
            } else {
                this.model.save(null, null, options);
            }
            return false;
        },

        deleteCrop: function deleteCrop() {
            var options = self._syncOptions();
            var success = options.success;

            options.success = function deleteSuccess() {
                success();
                alert('Crop deleted');
                window.history.back();
            };

            options.status.css("display", "block");
            this.model.destroy(options);
            return false;
        },

        close: function closeCrop() {
            jQuery(this.el).unbind();
            jQuery(this.el).empty();
        }});


    var HeaderView = Backbone.View.extend({
        template: underscore.template(jQuery('#template-header').html()),

        initialize: function initializeHeader() {
            this.render();
        },

        render: function renderHeader(eventName) {
            jQuery(this.el).html(this.template());
            return this;
        },

        events: {
            "click .new": "newCrop"
        },

        newCrop: function newCrop(event) {
            if (app.cropView) {
                app.cropView.close();
            }
            app.cropView = new CropView({model: new Crop()});
            jQuery('#content').html(app.cropView.render().el);
            return false;
        }});


    var AppRouter = Backbone.Router.extend({
        routes: {
            "": "list",
            "crops/:id": "crop-details"},

        initialize: function initializeRouter() {
            jQuery('#header').html(new HeaderView().render().el);
        },

        _getCollection: function _getCollection(options) {
            if (this.cropPlan) {
                options.success();
            } else {
                var self = this;
                var cropPlan = new CropPlan();
                var status = jQuery("#status-loading");
                status.css("display", "block");

                // XXX Backbone documentation says do not use fetch for on-page-load data.
                cropPlan.fetch({
                    success: function() {
                        status.css("display", "none");
                        self.cropPlan = cropPlan;
                        self.cropPlanView = new CropPlanView({model: cropPlan});
                        jQuery("#sidebar").html(self.cropPlanView.render().el);
                        options.success();
                    },
                    error: function() {
                        status.css("display", "none");
                        alert("Failed to fetch crop plan.");
                        options.error();
                    }});
            }
        },

        list: function list() {
            this._getCollection();
        },

        "crop-details": function crop_details(id) {
            var self = this;
            this._getCollection({
                success: function() {
                    self.crop = self.cropPlan.get(id);
                    self.cropView = new CropView({model: self.crop});
                    jQuery('#content').html(self.cropView.render().el);
                },
                error: function() {
                }});
        }});

    var app = new AppRouter();
    Backbone.history.start();
});
